import json
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import bcrypt
import io

from src.etl.extract import load_config, extract_url
from src.etl.load import load_df_to_db
from src.validation.schema_validation import build_dataframe_schema, valider_csv
from src.database.connection import engine, execute_sql_file, refresh_materialized_views
from src.config import SQL_DIR

import time
import pandas as pd
from functools import wraps
from datetime import datetime


def log(message: str, level: str = "INFO") -> None:
    """Affiche un message de log avec timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def log_step(step_name: str):
    """Décorateur pour logger le début/fin d'une étape avec durée."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            log(f"▶ Début: {step_name}", "STEP")
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            log(f"✓ Fin: {step_name} ({duration:.2f}s)", "STEP")
            return result
        return wrapper
    return decorator


load_dotenv()

def _quote_ident(name: str) -> str:
    """Quote identifiers safely for COPY SQL."""
    return f"\"{name.replace('\"', '\"\"')}\""


def copy_df_to_db(
    df: pd.DataFrame,
    table_name: str,
    engine,
    schema: str = "clean",
    chunk_size: int = 50000,
) -> None:
    """Bulk load DataFrame using COPY for speed (best for remote DBs)."""
    if df.empty:
        return

    full_table = f"{_quote_ident(schema)}.{_quote_ident(table_name)}"
    col_list = ", ".join(_quote_ident(col) for col in df.columns)
    copy_sql = (
        f"COPY {full_table} ({col_list}) FROM STDIN WITH CSV NULL '\\N'"
    )

    conn = engine.raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {_quote_ident(schema)}")
            cur.execute("SET app.etl_mode = 'true'")

            for start in range(0, len(df), chunk_size):
                chunk = df.iloc[start:start + chunk_size]
                buffer = io.StringIO()
                chunk.to_csv(
                    buffer,
                    index=False,
                    header=False,
                    na_rep="\\N",
                )
                buffer.seek(0)
                cur.copy_expert(copy_sql, buffer)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def coerce_int_columns(df: pd.DataFrame, columns: list[str], table_name: str) -> pd.DataFrame:
    """Force integer-typed columns to nullable ints to satisfy COPY."""
    for col in columns:
        if col not in df.columns:
            continue

        series = pd.to_numeric(df[col], errors="coerce")
        invalid_mask = series.notna() & (series % 1 != 0)
        if invalid_mask.any():
            log(
                f"  WARN: {table_name}.{col} a {invalid_mask.sum()} valeurs non entières → NULL",
                "WARN",
            )
        series = series.mask(invalid_mask)
        df[col] = series.astype("Int64")

    return df


def create_test_users(engine) -> None:
    """Crée les utilisateurs de test avec des hashs bcrypt valides."""
    test_users = [
        ("admin", "admin@secmar.local", "admin123", "admin"),
        ("editor", "editor@secmar.local", "editor123", "editor"),
        ("viewer", "viewer@secmar.local", "viewer123", "viewer"),
    ]

    with engine.connect() as conn:
        conn.execute(text("SET search_path TO clean"))

        for username, email, password, role in test_users:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            conn.execute(text("""
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (:username, :email, :password_hash, :role, true)
                ON CONFLICT (username) DO UPDATE SET
                    email = EXCLUDED.email,
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role,
            })
            print(f"   Utilisateur créé: {username} / {password} (role: {role})")

        conn.commit()


def apply_kpi_views(engine) -> None:
    """Applique les vues KPI depuis views_kpi.sql."""
    sql_file = SQL_DIR / "views_kpi.sql"

    if not sql_file.exists():
        print(f"   WARN: {sql_file} introuvable, skip")
        return

    sql_content = sql_file.read_text()

    with engine.connect() as conn:
        conn.execute(text(sql_content))
        conn.commit()

    print("   Vues KPI créées avec succès")


def pipeline_db_raw() -> None:
    """
    Pipeline ETL pour l'alimentation de la base de données RAW.

    Étapes du pipeline :
    1. Chargement de la configuration depuis le fichier YAML.
    2. Extraction des fichiers CSV depuis les URLs configurées.
    3. Construction dynamique des schémas de validation Pandera
       à partir de la section DATA_VALIDATION du fichier de configuration.
    4. Validation des fichiers CSV (mode lazy) et récupération
       des données valides uniquement.
    5. Chargement des données validées dans la base PostgreSQL
       dans le schéma RAW.

    Ce pipeline ne génère pas de rapport métier et s'arrête en cas
    d'erreur critique lors du chargement en base.

    Returns
    -------
    None
    """
    cfg = load_config("config/config.yml")

    # Étape 1 — Extraction des fichiers CSV
    _data_list = extract_url(
        dataset_url=cfg['EXTRACT']['dataset_url'],
        timeout_sec=cfg['EXTRACT']['timeout_sec'],
        output_dir=cfg['EXTRACT']['output_dir']
    )

    # Étape 2 — Construction des schémas de validation Pandera
    data_validation = cfg['DATA_VALIDATION']
    pandera_schemas = {}

    for schema_name, schema_def in data_validation.items():
        pandera_schemas[schema_name] = build_dataframe_schema(schema_def)

    # Étape 3 — Validation et chargement en base
    for schema_name, schema in pandera_schemas.items():
        csv_path = Path(f"{cfg['EXTRACT']['output_dir']}/{schema_name}.csv")

        # Validation des données (lazy pour récupérer toutes les erreurs)
        df = valider_csv(
            csv_path=csv_path,
            schema=schema,
            lazy=True
        )

        # Chargement des données validées dans le schéma RAW
        load_df_to_db(
            df=df,
            table_name=schema_name,
            engine=engine,
            if_exists="replace",
            schema="raw_test"  # à supprimer si non nécessaire
        )

def pipeline_db_cleaned(
    skip_extraction: bool = False,
    skip_validation: bool = False,
    skip_data_load: bool = False,
    skip_users: bool = False,
    schema_only: bool = False,
) -> None:
    """
    Pipeline ETL pour l'alimentation de la base de données CLEANED.

    Parameters
    ----------
    skip_extraction : bool
        Si True, saute l'extraction des CSV (étape 1).
    skip_validation : bool
        Si True, saute la validation et le merge (étapes 2-4).
    skip_data_load : bool
        Si True, saute le chargement en base (étape 6).
    skip_users : bool
        Si True, saute la création des utilisateurs test (étape 7).
    schema_only : bool
        Raccourci pour skip_extraction + skip_validation + skip_data_load.
        Utile pour ne modifier que le schéma/vues sans recharger les données.

    Returns
    -------
    None
    """
    pipeline_start = time.time()
    log("=" * 50)
    log("PIPELINE DB CLEANED - DÉMARRAGE", "START")
    log("=" * 50)

    # Raccourci schema_only
    if schema_only:
        skip_extraction = True
        skip_validation = True
        skip_data_load = True
        log("Mode schema_only activé (skip extraction/validation/data_load)")

    # Chargement config
    log("Chargement de la configuration...")
    cfg = load_config("config/config_clean.yml")
    log(f"  Dataset URL: {cfg['EXTRACT']['dataset_url']}")
    log(f"  Output dir: {cfg['EXTRACT']['output_dir']}")

    # Étape 1 — Extraction des fichiers CSV
    if not skip_extraction:
        log("-" * 40)
        log("▶ ÉTAPE 1: Extraction des fichiers CSV", "STEP")
        extract_start = time.time()
        _data_list = extract_url(
            dataset_url=cfg['EXTRACT']['dataset_url'],
            timeout_sec=cfg['EXTRACT']['timeout_sec'],
            output_dir=cfg['EXTRACT']['output_dir']
        )
        log(f"✓ Extraction terminée ({time.time() - extract_start:.2f}s)", "STEP")
    else:
        log("⏭ Étape 1 (Extraction) sautée")

    # Étapes 2-4 — Validation (schémas, CSV, merge)
    if not skip_validation:
        # Étape 2 — Construction des schémas de validation Pandera
        log("-" * 40)
        log("▶ ÉTAPE 2: Construction des schémas Pandera", "STEP")
        schema_start = time.time()
        data_validation = cfg['DATA_VALIDATION']
        pandera_schemas = {}

        for schema_name, schema_def in data_validation.items():
            log(f"  Building schema: {schema_name}")
            pandera_schemas[schema_name] = build_dataframe_schema(
                schema_def,
                strict_method=True
                )
        log(f"✓ Schémas construits: {list(pandera_schemas.keys())} ({time.time() - schema_start:.2f}s)", "STEP")

        # Étape 3 — Validation et chargement en base
        log("-" * 40)
        log("▶ ÉTAPE 3: Validation des CSV", "STEP")
        validation_start = time.time()

        dfs_validated = {}

        for schema_name, schema in pandera_schemas.items():
            csv_path = Path(f"{cfg['EXTRACT']['output_dir']}/{schema_name}.csv")
            log(f"  Validation de {schema_name}...")
            val_start = time.time()

            # Validation des données (lazy pour récupérer toutes les erreurs)
            df = valider_csv(
                csv_path=csv_path,
                schema=schema,
                lazy=True
            )
            df_filtered = df.loc[:, schema.columns.keys()]
            dfs_validated[schema_name] = df_filtered
            log(f"    → {len(df_filtered)} lignes valides ({time.time() - val_start:.2f}s)")

        log(f"✓ Validation terminée ({time.time() - validation_start:.2f}s)", "STEP")

        # Étape 4 — Merge des DataFrames
        log("-" * 40)
        log("▶ ÉTAPE 4: Merge operations + operations_stats", "STEP")
        merge_start = time.time()
        log(f"  operations: {len(dfs_validated['operations'])} lignes")
        log(f"  operations_stats: {len(dfs_validated['operations_stats'])} lignes")

        df_operations = pd.merge(
            dfs_validated["operations"],
            dfs_validated["operations_stats"],
            on="operation_id",
            how="left"
        )

        # Supprimer les deux DataFrames inutiles
        dfs_validated.pop("operations", None)
        dfs_validated.pop("operations_stats", None)

        # Ajouter le DataFrame fusionné
        dfs_validated["operations"] = df_operations
        log(f"✓ Merge terminé: {len(df_operations)} lignes ({time.time() - merge_start:.2f}s)", "STEP")
    else:
        log("⏭ Étapes 2-4 (Validation) sautées")
        dfs_validated = {}

    # Étape 5 — Création des tables SQL
    log("-" * 40)
    log("▶ ÉTAPE 5: Création des tables SQL", "STEP")
    sql_start = time.time()
    execute_sql_file("sql/clean_tables.sql", engine)
    log(f"✓ Tables créées ({time.time() - sql_start:.2f}s)", "STEP")

    # Étape 6 — Chargement en base
    if not skip_data_load:
        # Réorganiser l'ordre de chargement
        order = [
            "operations",
            "flotteurs",
            "resultats_humain"
        ]
        dfs_validated = {
            key: dfs_validated[key]
            for key in order
            if key in dfs_validated
        }
        log(f"  Ordre de chargement: {list(dfs_validated.keys())}")

        log("-" * 40)
        log("▶ ÉTAPE 6: Chargement en base de données", "STEP")
        load_start = time.time()

        triggers = [
            ("operations", "audit_operations"),
            ("flotteurs", "audit_flotteurs"),
            ("resultats_humain", "audit_resultats_humain"),
        ]

        # Préparation : truncate + désactiver triggers
        with engine.connect() as conn:
            conn.execute(text("SET search_path TO clean"))

            # Truncate tables in reverse FK order
            log("  Truncate des tables existantes...")
            for table_name in ["resultats_humain", "flotteurs", "operations"]:
                conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            conn.commit()
            log("  ✓ Tables vidées")

            # Désactiver les triggers d'audit
            log("  Désactivation des triggers d'audit...")
            for table, trigger in triggers:
                conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
            conn.commit()
            log("  ✓ Triggers désactivés")

        # Chargement bulk via COPY (rapide et robuste à la latence)
        rows_loaded = {}
        int_columns = {
            "operations": [
                "operation_id",
                "vent_direction",
                "vent_force",
                "mer_force",
                "maree_coefficient",
            ],
            "flotteurs": [
                "operation_id",
                "numero_ordre",
            ],
            "resultats_humain": [
                "operation_id",
                "nombre",
                "dont_nombre_blesse",
            ],
        }
        for schema_name, df in dfs_validated.items():
            try:
                total_rows = len(df)
                log(f"  Chargement de {schema_name} ({total_rows} lignes)...")
                table_start = time.time()

                df = coerce_int_columns(df, int_columns.get(schema_name, []), schema_name)
                copy_df_to_db(
                    df=df,
                    table_name=schema_name,
                    engine=engine,
                    schema="clean",
                )

                rows_loaded[schema_name] = total_rows
                speed = total_rows / (time.time() - table_start)
                log(f"    → {schema_name}: {total_rows} lignes ({time.time() - table_start:.2f}s, {speed:.0f} lignes/s)")
            except Exception as e:
                log(f"  ✗ Erreur sur clean.{schema_name}: {e}", "ERROR")
                continue

        # Réactiver les triggers d'audit
        with engine.connect() as conn:
            conn.execute(text("SET search_path TO clean"))
            log("  Réactivation des triggers d'audit...")
            for table, trigger in triggers:
                conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))
            conn.commit()
            log("  ✓ Triggers réactivés")

            # Log résumé audit
            log("  Enregistrement audit log...")
            for table_name, count in rows_loaded.items():
                conn.execute(text("""
                    INSERT INTO audit_log (table_name, operation_type, new_values, user_id)
                    VALUES (:table_name, 'ETL_LOAD', :summary, 'system')
                """), {
                    'table_name': table_name,
                    'summary': json.dumps({'rows_loaded': count, 'type': 'full_refresh'})
                })

            conn.commit()

        log(f"✓ Chargement terminé ({time.time() - load_start:.2f}s)", "STEP")
    else:
        log("⏭ Étape 6 (Chargement données) sautée")

    # Étape 7 — Création des utilisateurs de test
    if not skip_users:
        log("-" * 40)
        log("▶ ÉTAPE 7: Création des utilisateurs de test", "STEP")
        users_start = time.time()
        create_test_users(engine)
        log(f"✓ Utilisateurs créés ({time.time() - users_start:.2f}s)", "STEP")
    else:
        log("⏭ Étape 7 (Utilisateurs test) sautée")

    # Étape 8 — Application des vues KPI
    log("-" * 40)
    log("▶ ÉTAPE 8: Application des vues KPI", "STEP")
    kpi_start = time.time()
    apply_kpi_views(engine)
    log(f"✓ Vues KPI appliquées ({time.time() - kpi_start:.2f}s)", "STEP")

    # Étape 9 — Refresh de la vue matérialisée operations_stats
    log("-" * 40)
    log("▶ ÉTAPE 9: Refresh vue matérialisée operations_stats", "STEP")
    refresh_start = time.time()
    success = refresh_materialized_views()
    if success:
        log(f"✓ Vue matérialisée rafraîchie ({time.time() - refresh_start:.2f}s)", "STEP")
    else:
        log("⚠ Vue matérialisée non rafraîchie (peut-être pas encore créée)", "WARN")

    # Résumé final
    log("=" * 50)
    log("PIPELINE TERMINÉ AVEC SUCCÈS", "END")
    log(f"Durée totale: {time.time() - pipeline_start:.2f}s")
    log(f"Tables chargées: {rows_loaded}")
    log("=" * 50)

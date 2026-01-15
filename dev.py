#!/usr/bin/env python3
"""Script de développement pour charger les données SECMAR dans la BDD locale."""

import json
import sys
from pathlib import Path
import requests
import pandas as pd
import bcrypt
from sqlalchemy import create_engine, text

from src.config import DATABASE_URL, SQL_DIR, RAW_DIR

# URLs des CSV SECMAR
CSV_URLS = {
    "operations": "https://secmar.antoine-augusti.fr/operations.csv",
    "operations_stats": "https://secmar.antoine-augusti.fr/operations_stats.csv",
    "flotteurs": "https://secmar.antoine-augusti.fr/flotteurs.csv",
    "resultats_humain": "https://secmar.antoine-augusti.fr/resultats_humain.csv",
}

# Nombre d'opérations à charger (échantillon)
SAMPLE_SIZE = 10000


def download_csv(name: str, url: str) -> Path:
    """Télécharge un CSV si pas déjà présent."""
    filepath = RAW_DIR / f"{name}.csv"

    if filepath.exists():
        print(f"   {name}.csv existe déjà, skip")
        return filepath

    print(f"   Téléchargement {name}.csv...")
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"   OK ({filepath.stat().st_size / 1024 / 1024:.1f} MB)")
    return filepath


def download_all_csv() -> dict[str, Path]:
    """Télécharge tous les CSV nécessaires."""
    print("\n1. Téléchargement des CSV...")
    files = {}
    for name, url in CSV_URLS.items():
        files[name] = download_csv(name, url)
    return files


def load_and_merge_data(files: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Charge les CSV et merge operations + operations_stats."""
    print("\n2. Chargement et merge des données...")

    # Charger operations
    print("   Lecture operations.csv...")
    df_ops = pd.read_csv(files["operations"], low_memory=False)
    print(f"   {len(df_ops)} opérations totales")

    # Charger operations_stats (colonnes enrichies)
    print("   Lecture operations_stats.csv...")
    df_stats = pd.read_csv(files["operations_stats"], low_memory=False)

    # Colonnes enrichies à récupérer de operations_stats
    enriched_cols = [
        "operation_id",
        "est_jour_ferie", "est_vacances_scolaires", "phase_journee",
        "concerne_plongee", "implique_wingfoil",
        "distance_cote_metres", "distance_cote_milles_nautiques",
        "est_dans_stm", "nom_stm", "est_dans_dst", "nom_dst",
        "prefecture_maritime",
        "maree_port", "maree_coefficient", "maree_categorie",
    ]

    # Filtrer colonnes existantes
    available_cols = [c for c in enriched_cols if c in df_stats.columns]
    df_stats_subset = df_stats[available_cols]

    # Merge
    print("   Merge operations + operations_stats...")
    df_ops = df_ops.merge(df_stats_subset, on="operation_id", how="left")

    # Échantillon aléatoire
    print(f"   Échantillon de {SAMPLE_SIZE} opérations...")
    df_ops_sample = df_ops.sample(n=min(SAMPLE_SIZE, len(df_ops)), random_state=42)
    sample_ids = set(df_ops_sample["operation_id"].tolist())

    # Charger flotteurs filtrés
    print("   Lecture flotteurs.csv (filtrés)...")
    df_flotteurs = pd.read_csv(files["flotteurs"], low_memory=False)
    df_flotteurs = df_flotteurs[df_flotteurs["operation_id"].isin(sample_ids)]
    print(f"   {len(df_flotteurs)} flotteurs correspondants")

    # Charger resultats_humain filtrés
    print("   Lecture resultats_humain.csv (filtrés)...")
    df_resultats = pd.read_csv(files["resultats_humain"], low_memory=False)
    df_resultats = df_resultats[df_resultats["operation_id"].isin(sample_ids)]
    print(f"   {len(df_resultats)} résultats correspondants")

    return df_ops_sample, df_flotteurs, df_resultats


def prepare_operations_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prépare le DataFrame operations pour le chargement."""
    # Colonnes de la table operations (schema clean)
    table_cols = [
        "operation_id", "type_operation", "numero_sitrep", "cross_sitrep",
        "sous_type_operation", "pourquoi_alerte", "moyen_alerte", "qui_alerte",
        "categorie_qui_alerte", "cross", "departement", "est_metropolitain",
        "zone_responsabilite", "latitude", "longitude", "evenement",
        "categorie_evenement", "autorite", "seconde_autorite",
        "vent_direction", "vent_direction_categorie", "vent_force", "mer_force",
        "date_heure_reception_alerte", "date_heure_fin_operation",
        "fuseau_horaire", "systeme_source",
        # Colonnes enrichies
        "est_jour_ferie", "est_vacances_scolaires", "phase_journee",
        "concerne_plongee", "implique_wingfoil",
        "distance_cote_metres", "distance_cote_milles_nautiques",
        "est_dans_stm", "nom_stm", "est_dans_dst", "nom_dst",
        "prefecture_maritime", "maree_port", "maree_coefficient", "maree_categorie",
    ]

    # Garder seulement les colonnes existantes
    available_cols = [c for c in table_cols if c in df.columns]
    df_clean = df[available_cols].copy()

    # Convertir les dates
    date_cols = ["date_heure_reception_alerte", "date_heure_fin_operation"]
    for col in date_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_datetime(df_clean[col], errors="coerce")

    return df_clean


def prepare_flotteurs_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prépare le DataFrame flotteurs pour le chargement."""
    table_cols = [
        "operation_id", "numero_ordre", "type_flotteur", "categorie_flotteur",
        "pavillon", "numero_immatriculation", "resultat_flotteur",
    ]
    available_cols = [c for c in table_cols if c in df.columns]
    return df[available_cols].copy()


def prepare_resultats_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prépare le DataFrame resultats_humain pour le chargement."""
    table_cols = [
        "operation_id", "categorie_personne", "resultat_humain",
        "nombre", "dont_nombre_blesse",
    ]
    available_cols = [c for c in table_cols if c in df.columns]
    return df[available_cols].copy()


def load_to_database(df_ops: pd.DataFrame, df_flotteurs: pd.DataFrame, df_resultats: pd.DataFrame):
    """Charge les données dans PostgreSQL.

    Utilise le mode ETL pour désactiver l'audit granulaire pendant le chargement.
    Un résumé est logué à la fin (une ligne par table au lieu de milliers).
    """
    print("\n3. Chargement dans PostgreSQL...")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Activer le mode ETL (désactive l'audit granulaire pendant le chargement)
        conn.execute(text("SET LOCAL app.etl_mode = 'true'"))
        conn.execute(text("SET search_path TO clean"))

        # Truncate tables (ordre inverse des FK)
        print("   Truncate tables...")
        conn.execute(text("TRUNCATE resultats_humain, flotteurs, operations CASCADE"))
        conn.commit()

        # Re-activer le mode ETL après le commit (SET LOCAL est réinitialisé)
        conn.execute(text("SET LOCAL app.etl_mode = 'true'"))
        conn.execute(text("SET search_path TO clean"))

        # Charger operations
        print(f"   Chargement operations ({len(df_ops)} lignes)...")
        df_ops_clean = prepare_operations_df(df_ops)
        df_ops_clean.to_sql("operations", conn, schema="clean", if_exists="append", index=False)

        # Charger flotteurs
        print(f"   Chargement flotteurs ({len(df_flotteurs)} lignes)...")
        df_flotteurs_clean = prepare_flotteurs_df(df_flotteurs)
        df_flotteurs_clean.to_sql("flotteurs", conn, schema="clean", if_exists="append", index=False)

        # Charger resultats_humain
        print(f"   Chargement resultats_humain ({len(df_resultats)} lignes)...")
        df_resultats_clean = prepare_resultats_df(df_resultats)
        df_resultats_clean.to_sql("resultats_humain", conn, schema="clean", if_exists="append", index=False)

        # Logger un résumé pour l'audit (une ligne par table au lieu de milliers)
        print("   Enregistrement résumé audit...")
        conn.execute(text("""
            INSERT INTO audit_log (table_name, operation_type, new_values, user_id)
            VALUES
                ('operations', 'ETL_LOAD', :ops_summary, 'system'),
                ('flotteurs', 'ETL_LOAD', :flot_summary, 'system'),
                ('resultats_humain', 'ETL_LOAD', :res_summary, 'system')
        """), {
            'ops_summary': json.dumps({'rows_loaded': len(df_ops_clean), 'type': 'full_refresh'}),
            'flot_summary': json.dumps({'rows_loaded': len(df_flotteurs_clean), 'type': 'full_refresh'}),
            'res_summary': json.dumps({'rows_loaded': len(df_resultats_clean), 'type': 'full_refresh'})
        })

        conn.commit()
        print("   OK")


def apply_kpi_views():
    """Applique les vues KPI depuis views_kpi.sql."""
    print("\n4. Application des vues KPI...")
    sql_file = SQL_DIR / "views_kpi.sql"

    if not sql_file.exists():
        print(f"   WARN: {sql_file} introuvable, skip")
        return

    engine = create_engine(DATABASE_URL)
    sql_content = sql_file.read_text()

    with engine.connect() as conn:
        # Exécuter le fichier SQL complet
        conn.execute(text(sql_content))
        conn.commit()

    print("   Vues KPI créées avec succès")


def verify_data():
    """Vérifie les données chargées."""
    print("\n5. Vérification...")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        conn.execute(text("SET search_path TO clean"))

        ops_count = conn.execute(text("SELECT COUNT(*) FROM operations")).scalar()
        flot_count = conn.execute(text("SELECT COUNT(*) FROM flotteurs")).scalar()
        res_count = conn.execute(text("SELECT COUNT(*) FROM resultats_humain")).scalar()

        print(f"   operations: {ops_count} lignes")
        print(f"   flotteurs: {flot_count} lignes")
        print(f"   resultats_humain: {res_count} lignes")

        # Vérifier les vues
        try:
            kpi_count = conn.execute(text("SELECT COUNT(*) FROM v_kpi_securite_mensuel")).scalar()
            print(f"   v_kpi_securite_mensuel: {kpi_count} périodes")
        except Exception:
            print("   WARN: Vues KPI non disponibles")


def create_test_users():
    """Crée les utilisateurs de test avec des hashs bcrypt valides."""
    print("\n4. Création des utilisateurs de test...")
    engine = create_engine(DATABASE_URL)

    # Utilisateurs de test avec leurs mots de passe
    test_users = [
        ("admin", "admin@secmar.local", "admin123", "admin"),
        ("editor", "editor@secmar.local", "editor123", "editor"),
        ("viewer", "viewer@secmar.local", "viewer123", "viewer"),
    ]

    with engine.connect() as conn:
        conn.execute(text("SET search_path TO clean"))

        for username, email, password, role in test_users:
            # Générer le hash bcrypt
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            # Insérer ou mettre à jour l'utilisateur
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
            print(f"   {username} / {password} (role: {role})")

        conn.commit()


def reset_database():
    """Drop le schéma clean et recrée les tables via stub_tables.sql."""
    sql_file = SQL_DIR / "stub_tables.sql"

    if not sql_file.exists():
        print(f"Erreur: {sql_file} introuvable")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)

    print("Connexion à la base...")
    print(f"URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    with engine.connect() as conn:
        print("\n1. DROP SCHEMA clean CASCADE...")
        conn.execute(text("DROP SCHEMA IF EXISTS clean CASCADE"))
        conn.commit()
        print("   OK")

        print(f"\n2. Exécution de {sql_file.name}...")
        sql_content = sql_file.read_text()
        conn.execute(text(sql_content))
        conn.commit()
        print("   OK")

        print("\n3. Vérification...")
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'clean'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"   Tables créées: {', '.join(tables)}")

    # Créer les utilisateurs de test
    create_test_users()

    print("\nBase de données réinitialisée avec succès!")


def load_sample_data():
    """Pipeline complet: télécharge CSV, charge données, applique vues."""
    print("=" * 60)
    print("Chargement des données SECMAR (échantillon)")
    print("=" * 60)

    # 1. Télécharger les CSV
    files = download_all_csv()

    # 2. Charger et merger
    df_ops, df_flotteurs, df_resultats = load_and_merge_data(files)

    # 3. Reset la BDD et charger
    reset_database()
    load_to_database(df_ops, df_flotteurs, df_resultats)

    # 4. Appliquer les vues KPI
    apply_kpi_views()

    # 5. Vérifier
    verify_data()

    print("\n" + "=" * 60)
    print("Chargement terminé! Tu peux lancer Streamlit:")
    print("  streamlit run app/main.py")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_database()
    else:
        load_sample_data()

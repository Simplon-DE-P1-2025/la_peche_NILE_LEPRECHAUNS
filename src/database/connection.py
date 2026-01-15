"""
connection.py - Se connecter à PostgreSQL sur Render.com avec SQLAlchemy
"""

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional
from sqlalchemy.engine import Engine
from pathlib import Path
import os


def create_postgres_engine(
    host: str, database: str, user: str, password: str, port: int = 5432
) -> Optional[Engine]:

    try:
        # Créer l'URL de connexion
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"

        # Créer le moteur
        engine = create_engine(url, pool_pre_ping=True)

        print(f"✅ Connexion réussie à {database}")
        return engine

    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")
        return None


'''def get_session():
    """
    Créer une session pour parler à la base de données

    Retour
    ------
    sqlalchemy.orm.Session
        Session de base de données
    """
    if SessionLocal is None:
        print("❌ Pas de connexion à la base de données!")
        return None
    return SessionLocal()'''

"""Connexion à la base de données - STUB pour CRUD.

Ce fichier fournit les fonctions de connexion nécessaires pour le CRUD et l'analytics.
L'équipier doit valider/compléter ce fichier.

Fonctions fournies :
- get_session() : Context manager pour session SQLAlchemy (CRUD ORM)
- get_raw_connection() : Context manager pour connexion raw (bulk, analytics)
- set_session_user() : Définir l'utilisateur pour l'audit
- execute_raw_sql() : Exécuter du SQL raw et retourner les résultats
- test_connection() : Tester la connexion à la BDD
"""

from contextlib import contextmanager
from typing import Generator, Any

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

from src.config import DATABASE_URL, DB_SCHEMA, DB_ECHO, DB_POOL_SIZE, DB_MAX_OVERFLOW

# Base class for all SQLAlchemy models - utilise le schéma configuré (clean par défaut)
Base = declarative_base(metadata=MetaData(schema=DB_SCHEMA))


# =============================================================================
# Engine SQLAlchemy
# =============================================================================
engine = create_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    poolclass=QueuePool,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_pre_ping=True,
)

# Factory de sessions
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# =============================================================================
# Context Managers
# =============================================================================
@contextmanager
def get_session(schema: str = None) -> Generator[Session, None, None]:
    """Context manager pour obtenir une session SQLAlchemy.

    Args:
        schema: Schéma à utiliser (défaut: DB_SCHEMA de config)

    Usage:
        with get_session() as session:
            operations = session.query(Operation).all()
            session.add(new_operation)
            # commit automatique à la sortie
    """
    session = SessionLocal()
    try:
        # Définir le search_path vers le schéma demandé
        target_schema = schema or DB_SCHEMA
        session.execute(text(f"SET search_path TO {target_schema}"))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_raw_connection(schema: str = None):
    """Context manager pour connexion raw (psycopg2).

    Args:
        schema: Schéma à utiliser (défaut: DB_SCHEMA de config)

    Utile pour :
    - Bulk operations avec execute_values
    - Requêtes SQL complexes
    - COPY FROM/TO

    Usage:
        with get_raw_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM operations")

        # Pour schéma raw:
        with get_raw_connection(schema='raw') as conn:
            ...
    """
    conn = engine.raw_connection()
    try:
        # Définir le search_path vers le schéma demandé
        target_schema = schema or DB_SCHEMA
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {target_schema}")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def etl_session(schema: str = None) -> Generator[Session, None, None]:
    """Context manager pour opérations ETL (audit granulaire désactivé).

    Pendant les opérations ETL, l'audit ne génère pas d'entrées par ligne.
    À la fin de l'ETL, vous devez logger manuellement un résumé.

    Args:
        schema: Schéma à utiliser (défaut: DB_SCHEMA de config)

    Usage:
        with etl_session() as session:
            # Toutes les opérations ici ne génèrent PAS d'audit granulaire
            session.execute(text("TRUNCATE operations CASCADE"))
            # ... bulk inserts ...

            # Logger un résumé à la fin
            session.execute(text('''
                INSERT INTO audit_log (table_name, operation_type, new_values, user_id)
                VALUES ('operations', 'ETL_LOAD', '{"rows": 10000}', 'system')
            '''))
    """
    session = SessionLocal()
    try:
        target_schema = schema or DB_SCHEMA
        session.execute(text(f"SET search_path TO {target_schema}"))
        session.execute(text("SET LOCAL app.etl_mode = 'true'"))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# Fonctions utilitaires
# =============================================================================
def set_session_user(session: Session, username: str) -> None:
    """Définir l'utilisateur courant pour l'audit.

    Les triggers PostgreSQL utilisent current_setting('app.current_user')
    pour logger qui a fait la modification.

    Args:
        session: Session SQLAlchemy active
        username: Nom de l'utilisateur à logger
    """
    # Échapper le username pour éviter les injections
    safe_username = username.replace("'", "''")
    session.execute(text(f"SET LOCAL \"app.current_user\" = '{safe_username}'"))


def execute_raw_sql(sql: str, params: dict = None) -> list[dict]:
    """Exécuter du SQL raw et retourner les résultats.

    Idéal pour les requêtes analytics complexes.

    Args:
        sql: Requête SQL (peut contenir des :param)
        params: Dictionnaire de paramètres

    Returns:
        Liste de dictionnaires (un par ligne)

    Usage:
        results = execute_raw_sql(
            "SELECT cross, COUNT(*) as total FROM operations GROUP BY cross",
        )
        for row in results:
            print(row["cross"], row["total"])
    """
    with get_session() as session:
        result = session.execute(text(sql), params or {})
        if result.returns_rows:
            return [dict(row._mapping) for row in result]
        return []


def test_connection() -> bool:
    """Tester la connexion à la base de données.

    Returns:
        True si la connexion fonctionne, False sinon
    """
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Erreur de connexion: {e}")
        return False


# =============================================================================
# Initialisation des tables (pour développement)
# =============================================================================
def init_tables() -> None:
    """Créer les tables à partir des modèles SQLAlchemy.

    Note: En production, utiliser les scripts SQL du dossier sql/
    """
    from src.database.models import Base

    Base.metadata.create_all(engine)
    print("Tables créées avec succès")


def drop_tables() -> None:
    """Supprimer toutes les tables (DANGER - développement uniquement)."""
    from src.database.models import Base

    Base.metadata.drop_all(engine)
    print("Tables supprimées")

def refresh_materialized_views() -> bool:
    """Rafraîchir les vues matérialisées (à appeler après ETL).

    Vues rafraîchies:
    - operations_stats: stats par opération (source pour les autres)
    - v_kpi_global: KPIs globaux pré-calculés
    - v_kpi_annuel: stats annuelles pré-calculées
    - v_kpi_cross: stats par CROSS pré-calculées
    - v_kpi_yoy_cross_actifs: Year-over-Year pour CROSS actifs
    - v_kpi_cross_benchmark_mv: Performance benchmark CROSS (Phase 4)
    - v_kpi_flotteurs_categorie_mv: Stats flotteurs par catégorie (Phase 4)
    - v_kpi_alertes_anomalies_mv: Alertes et anomalies avec z-scores
    - v_kpi_securite_mensuel_mv: Sécurité mensuelle pré-calculée

    Returns:
        True si le rafraîchissement a réussi, False sinon
    """
    try:
        with get_session() as session:
            # Vérifier si operations_stats est une vue matérialisée
            result = session.execute(text("""
                SELECT 1 FROM pg_matviews
                WHERE matviewname = 'operations_stats' AND schemaname = 'clean'
            """))
            if not result.fetchone():
                print("operations_stats n'est pas une vue matérialisée")
                return False

            # Rafraîchir operations_stats en premier (source pour les autres vues)
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY operations_stats"))
            session.execute(text("ANALYZE operations_stats"))
            print("  ✓ operations_stats rafraîchie")

            # Rafraîchir les vues KPI dépendantes
            # v_kpi_global n'a pas d'index unique, donc pas CONCURRENTLY
            session.execute(text("REFRESH MATERIALIZED VIEW v_kpi_global"))
            print("  ✓ v_kpi_global rafraîchie")

            # v_kpi_annuel et v_kpi_cross ont des index uniques
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_annuel"))
            print("  ✓ v_kpi_annuel rafraîchie")

            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_cross"))
            print("  ✓ v_kpi_cross rafraîchie")

            # v_kpi_yoy_cross_actifs pour les comparatifs YoY des CROSS actifs
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_yoy_cross_actifs"))
            print("  ✓ v_kpi_yoy_cross_actifs rafraîchie")

            # v_kpi_cross_benchmark_mv pour les performances CROSS (Phase 4)
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_cross_benchmark_mv"))
            print("  ✓ v_kpi_cross_benchmark_mv rafraîchie")

            # v_kpi_flotteurs_categorie_mv pour les stats flotteurs (Phase 4)
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_flotteurs_categorie_mv"))
            print("  ✓ v_kpi_flotteurs_categorie_mv rafraîchie")

            # v_kpi_flotteurs_categorie_cross_actifs_mv pour les CROSS actifs
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_flotteurs_categorie_cross_actifs_mv"))
            print("  ✓ v_kpi_flotteurs_categorie_cross_actifs_mv rafraîchie")

            # v_kpi_flotteurs_analyse_cross_actifs_mv pour les CROSS actifs
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_flotteurs_analyse_cross_actifs_mv"))
            print("  ✓ v_kpi_flotteurs_analyse_cross_actifs_mv rafraîchie")

            # v_kpi_alertes_anomalies_mv pour les alertes et anomalies
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_alertes_anomalies_mv"))
            print("  ✓ v_kpi_alertes_anomalies_mv rafraîchie")

            # v_kpi_alertes_anomalies_cross_actifs_mv pour les CROSS actifs
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_alertes_anomalies_cross_actifs_mv"))
            print("  ✓ v_kpi_alertes_anomalies_cross_actifs_mv rafraîchie")

            # v_kpi_securite_mensuel_mv pour la sécurité mensuelle
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_securite_mensuel_mv"))
            print("  ✓ v_kpi_securite_mensuel_mv rafraîchie")

            # v_kpi_securite_mensuel_cross_actifs_mv pour les CROSS actifs
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_securite_mensuel_cross_actifs_mv"))
            print("  ✓ v_kpi_securite_mensuel_cross_actifs_mv rafraîchie")

            # Vues temporelles et météo pour les CROSS actifs
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_saisonnalite_mensuelle_cross_actifs_mv"))
            print("  ✓ v_kpi_saisonnalite_mensuelle_cross_actifs_mv rafraîchie")

            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_phase_journee_cross_actifs_mv"))
            print("  ✓ v_kpi_phase_journee_cross_actifs_mv rafraîchie")

            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_impact_vacances_cross_actifs_mv"))
            print("  ✓ v_kpi_impact_vacances_cross_actifs_mv rafraîchie")

            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_meteo_correlation_cross_actifs_mv"))
            print("  ✓ v_kpi_meteo_correlation_cross_actifs_mv rafraîchie")

        print("Vues matérialisées rafraîchies avec succès")
        return True
    except Exception as e:
        print(f"Erreur lors du rafraîchissement: {e}")
        return False


def refresh_materialized_views_async() -> None:
    """Rafraîchir les vues matérialisées en arrière-plan (non-bloquant).

    Lance le refresh dans un thread séparé pour ne pas bloquer l'utilisateur.
    Utile après les opérations CRUD pour mettre à jour le dashboard.
    """
    import threading

    thread = threading.Thread(target=refresh_materialized_views, daemon=True)
    thread.start()


def invalidate_stats_cache() -> None:
    """Invalide le cache Streamlit des fonctions analytics.

    À appeler après les opérations CRUD pour forcer le re-fetch
    des données sur le dashboard.
    """
    try:
        import streamlit as st
        st.cache_data.clear()
        st.cache_resource.clear()
    except Exception:
        pass  # Pas en contexte Streamlit ou erreur - on ignore


def check_materialized_view_status() -> dict:
    """Vérifier le statut de la vue matérialisée operations_stats.

    Returns:
        Dictionnaire avec le statut et les infos de la vue
    """
    try:
        with get_session() as session:
            # Vérifier si c'est une vue matérialisée
            result = session.execute(text("""
                SELECT
                    'operations_stats' as view_name,
                    CASE
                        WHEN EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = 'operations_stats' AND schemaname = 'clean')
                        THEN 'MATERIALIZED'
                        WHEN EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'operations_stats' AND schemaname = 'clean')
                        THEN 'REGULAR'
                        ELSE 'NOT_FOUND'
                    END as view_type
            """))
            row = result.fetchone()
            view_type = row[1] if row else "NOT_FOUND"

            # Compter les lignes
            count_result = session.execute(text("SELECT COUNT(*) FROM operations_stats"))
            row_count = count_result.scalar() or 0

            return {
                "view_type": view_type,
                "row_count": row_count,
                "is_optimized": view_type == "MATERIALIZED",
            }
    except Exception as e:
        return {
            "view_type": "ERROR",
            "row_count": 0,
            "is_optimized": False,
            "error": str(e),
        }


def execute_sql_file(sql_file: str, engine: Engine):
    """
    Exécute le contenu d'un fichier SQL avec SQLAlchemy.

    Args:
        sql_file (Path): chemin vers le fichier .sql
        engine (Engine): moteur SQLAlchemy
    """
    sql_file = Path(sql_file)

    if not sql_file.exists():
        raise FileNotFoundError(f"Fichier SQL introuvable : {sql_file}")

    sql = sql_file.read_text(encoding="utf-8")

    with engine.begin() as conn:
        conn.execute(text(sql))

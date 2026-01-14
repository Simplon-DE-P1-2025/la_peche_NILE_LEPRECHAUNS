"""
connection.py - Se connecter à PostgreSQL sur Render.com avec SQLAlchemy
"""

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional
from sqlalchemy.engine import Engine
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

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.config import DATABASE_URL, DB_ECHO, DB_POOL_SIZE, DB_MAX_OVERFLOW


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
def get_session() -> Generator[Session, None, None]:
    """Context manager pour obtenir une session SQLAlchemy.

    Usage:
        with get_session() as session:
            operations = session.query(Operation).all()
            session.add(new_operation)
            # commit automatique à la sortie
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_raw_connection():
    """Context manager pour connexion raw (psycopg2).

    Utile pour :
    - Bulk operations avec execute_values
    - Requêtes SQL complexes
    - COPY FROM/TO

    Usage:
        with get_raw_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM operations")
    """
    conn = engine.raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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

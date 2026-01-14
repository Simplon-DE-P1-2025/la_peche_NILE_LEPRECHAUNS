"""
connection.py - Se connecter à PostgreSQL sur Render.com avec SQLAlchemy
"""

from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional
from sqlalchemy.engine import Engine
import os
import pandas as pd


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
    return SessionLocal()
"""
models.py - Définir les 4 tables de la base de données

"""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from .connection import Base


class Operation(Base):
    """Table des opérations de sauvetage"""
    __tablename__ = "operations"

    # Colonnes
    operation_id = Column(Integer, primary_key=True)
    date_heure_reception = Column(DateTime)
    cross_nom = Column(String(100))
    evenement_type = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    #Relation Resultat et flotteur

class ResultatHumain(Base):
    """Table du bilan humain (victimes, sauvetages...)"""
    __tablename__ = "bilan_humain"

    # Colonnes
    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_id = Column(Integer, ForeignKey("operations.operation_id"))
    nb_personnes_impliquees = Column(Integer)
    nb_decedes = Column(Integer)
    nb_sains_et_saufs = Column(Integer)


class AuditLog(Base):
    """Table pour tracer les modifications"""
    __tablename__ = "audit_logs"

    # Colonnes
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime)
    utilisateur = Column(String(100))
    action = Column(String(50))  # INSERT, UPDATE, DELETE
    table_nom = Column(String(100))

class Users(Base):
    __tablename__ = "users"

    # Colonnes
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True)
    email = Column(String(200), unique=True)
    password_hash = Column(String(255))


class Flotteur(Base):
    __tablename__ = "flotteurs"

    # Colonnes
    id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100))
    type_flotteur = Column(String(100))
    operation_id = Column(Integer, ForeignKey("operations.operation_id"))
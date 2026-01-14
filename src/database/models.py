"""
models.py - Définir les tables avec relations selon le MCD maritime
Version compatible SQLAlchemy 1.4+ et 2.0+
"""
from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .connection import Base


class Operation(Base):
    """Table principale des opérations de sauvetage SECMAR"""
    __tablename__ = "operations"
    operation_id = Column(Integer, primary_key=True)
    date_heure_reception = Column(DateTime, nullable=False)
    cross_nom = Column(String(100))
    evenement_type = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    zone_marine = Column(String(100))
    departement = Column(String(100))
    commune = Column(String(200))
    vent_direction = Column(String(50))
    vent_force = Column(Integer)
    mer_force = Column(Integer)
    temperature_eau = Column(Float)
    assistance_type = Column(String(200))
    categorie = Column(String(100))
    phase_journee = Column(String(50))
    saison = Column(String(50))
    pavillon = Column(String(100))
    commentaire = Column(Text)

    # Relations (1 opération → plusieurs flotteurs, 1 bilan)
    flotteurs = relationship(
        "Flotteur",
        back_populates="operation",
        cascade="all, delete-orphan"
    )

    resultat_humain = relationship(
        "ResultatHumain",
        back_populates="operation",
        uselist=False,  # 1 à 1
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Operation(id={self.operation_id}, type={self.evenement_type})>"


class Flotteur(Base):
    """Table des flotteurs impliqués dans l'opération (navires en détresse)"""
    __tablename__ = "flotteurs"

    # Clé primaire
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Clé étrangère
    operation_id = Column(
        Integer,
        ForeignKey("operations.operation_id", ondelete="CASCADE"),
        nullable=False
    )

    # Informations sur le flotteur
    nom = Column(String(100))
    type_flotteur = Column(String(100))
    longueur = Column(Float)
    largeur = Column(Float)
    materiau = Column(String(50))
    propulsion = Column(String(100))
    immatriculation = Column(String(100))
    port_attache = Column(String(200))
    annee_construction = Column(Integer)
    puissance_moteur = Column(Integer)
    jauge = Column(Float)

    # Relation
    operation = relationship("Operation", back_populates="flotteurs")

    def __repr__(self):
        return f"<Flotteur(id={self.id}, nom={self.nom}, type={self.type_flotteur})>"


class ResultatHumain(Base):
    """Table du bilan humain de l'opération"""
    __tablename__ = "bilan_humain"

    # Clé primaire
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Clé étrangère (1 à 1)
    operation_id = Column(
        Integer,
        ForeignKey("operations.operation_id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Compteurs humains
    nb_personnes_impliquees = Column(Integer, default=0)
    nb_personnes_secourues = Column(Integer, default=0)
    nb_personnes_assistees = Column(Integer, default=0)
    nb_decedes = Column(Integer, default=0)
    nb_disparus = Column(Integer, default=0)
    nb_blesses = Column(Integer, default=0)
    nb_blesses_legers = Column(Integer, default=0)
    nb_blesses_graves = Column(Integer, default=0)
    nb_sains_et_saufs = Column(Integer, default=0)
    nb_indemnes = Column(Integer, default=0)

    # Relation
    operation = relationship("Operation", back_populates="resultat_humain")

    def __repr__(self):
        return f"<ResultatHumain(operation_id={self.operation_id}, impliquées={self.nb_personnes_impliquees})>"


class AuditLog(Base):
    """Table pour tracer les modifications"""
    __tablename__ = "audit_logs"

    # Colonnes
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    utilisateur = Column(String(100))
    action = Column(String(50))  # INSERT, UPDATE, DELETE
    table_nom = Column(String(100))

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, table={self.table_nom})>"


class Users(Base):
    """Table des utilisateurs pour l'authentification"""
    __tablename__ = "users"

    # Colonnes
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"

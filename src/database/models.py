"""Modèles SQLAlchemy - STUB pour CRUD.

Ces modèles définissent la structure des tables.
L'équipier doit valider/compléter avec tous les champs.

Tables :
- Operation : Opérations de sauvetage maritime
- Flotteur : Embarcations impliquées
- ResultatHumain : Bilans humains
- OperationStats : Statistiques par opération -> sera une view
- User : Utilisateurs de l'application
- AuditLog : Journal d'audit (lecture seule, alimenté par triggers)
"""

from datetime import date, time, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Time,
    Text,
    DECIMAL,
    ForeignKey,
    TIMESTAMP,
    Boolean,
    JSON,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles."""

    pass


# =============================================================================
# Table Operations
# =============================================================================
class Operation(Base):
    """Opérations de sauvetage maritime."""

    __tablename__ = "operations"

    # Clé primaire
    operation_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Informations générales
    numero_sitrep: Mapped[Optional[str]] = mapped_column(String(50))
    date_operation: Mapped[Optional[date]] = mapped_column(Date)
    heure_operation: Mapped[Optional[time]] = mapped_column(Time)
    type_operation: Mapped[Optional[str]] = mapped_column(String(100))
    sous_type_operation: Mapped[Optional[str]] = mapped_column(String(100))

    # Localisation
    cross: Mapped[Optional[str]] = mapped_column(String(50))
    departement: Mapped[Optional[str]] = mapped_column(String(3))
    zone_responsabilite: Mapped[Optional[str]] = mapped_column(String(50))
    latitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 6))
    longitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 6))

    # Conditions météo
    vent_direction: Mapped[Optional[int]] = mapped_column(Integer)
    vent_force: Mapped[Optional[int]] = mapped_column(Integer)
    mer_force: Mapped[Optional[int]] = mapped_column(Integer)
    meteo: Mapped[Optional[str]] = mapped_column(String(100))

    # Statistiques
    nombre_personnes_impliquees: Mapped[int] = mapped_column(Integer, default=0)
    nombre_moyens_engages: Mapped[int] = mapped_column(Integer, default=0)
    duree_intervention: Mapped[Optional[int]] = mapped_column(Integer)

    # Enrichissement MCD
    est_jour_ferie: Mapped[bool] = mapped_column(Boolean, default=False)
    est_vacances_scolaires: Mapped[bool] = mapped_column(Boolean, default=False)
    phase_journee: Mapped[Optional[str]] = mapped_column(String(50))
    concerne_plongee: Mapped[bool] = mapped_column(Boolean, default=False)
    implique_wingfoil: Mapped[bool] = mapped_column(Boolean, default=False)
    distance_cote_metres: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    distance_cote_milles_nautiques: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 4))
    est_dans_stm: Mapped[bool] = mapped_column(Boolean, default=False)
    nom_stm: Mapped[Optional[str]] = mapped_column(String(100))
    est_dans_dst: Mapped[bool] = mapped_column(Boolean, default=False)
    nom_dst: Mapped[Optional[str]] = mapped_column(String(100))
    prefecture_maritime: Mapped[Optional[str]] = mapped_column(String(100))
    maree_port: Mapped[Optional[str]] = mapped_column(String(100))
    maree_coefficient: Mapped[Optional[int]] = mapped_column(Integer)
    maree_categorie: Mapped[Optional[str]] = mapped_column(String(50))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relations
    flotteurs: Mapped[List["Flotteur"]] = relationship(
        "Flotteur",
        back_populates="operation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    resultats_humain: Mapped[List["ResultatHumain"]] = relationship(
        "ResultatHumain",
        back_populates="operation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Operation {self.operation_id} - {self.date_operation}>"

    def to_dict(self) -> dict:
        """Convertir en dictionnaire."""
        return {
            "operation_id": self.operation_id,
            "numero_sitrep": self.numero_sitrep,
            "date_operation": str(self.date_operation) if self.date_operation else None,
            "type_operation": self.type_operation,
            "cross": self.cross,
            "departement": self.departement,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "nombre_personnes_impliquees": self.nombre_personnes_impliquees,
            "duree_intervention": self.duree_intervention,
        }


# =============================================================================
# Table Flotteurs
# =============================================================================
class Flotteur(Base):
    """Embarcations impliquées dans les opérations."""

    __tablename__ = "flotteurs"

    flotteur_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    operation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("operations.operation_id", ondelete="CASCADE"),
        nullable=False,
    )
    numero_ordre: Mapped[Optional[int]] = mapped_column(Integer)

    type_flotteur: Mapped[Optional[str]] = mapped_column(String(100))
    categorie_flotteur: Mapped[Optional[str]] = mapped_column(String(100))
    pavillon: Mapped[Optional[str]] = mapped_column(String(50))
    immatriculation: Mapped[Optional[str]] = mapped_column(String(50))
    nom_flotteur: Mapped[Optional[str]] = mapped_column(String(100))
    longueur: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(6, 2))
    nombre_personnes: Mapped[int] = mapped_column(Integer, default=0)
    resultat_flotteur: Mapped[Optional[str]] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    # Relation inverse
    operation: Mapped["Operation"] = relationship(
        "Operation", back_populates="flotteurs"
    )

    def __repr__(self) -> str:
        return f"<Flotteur {self.flotteur_id} - {self.type_flotteur}>"


# =============================================================================
# Table Résultats Humains
# =============================================================================
class ResultatHumain(Base):
    """Bilans humains des opérations."""

    __tablename__ = "resultats_humain"

    resultat_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    operation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("operations.operation_id", ondelete="CASCADE"),
        nullable=False,
    )

    categorie_personne: Mapped[Optional[str]] = mapped_column(String(50))
    resultat_humain: Mapped[Optional[str]] = mapped_column(String(50))
    nombre: Mapped[int] = mapped_column(Integer, default=0)
    dont_nombre_blesse: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    # Relation inverse
    operation: Mapped["Operation"] = relationship(
        "Operation", back_populates="resultats_humain"
    )

    def __repr__(self) -> str:
        return f"<ResultatHumain {self.resultat_id} - {self.resultat_humain}>"


# =============================================================================
# VIEW Operations Stats (lecture seule - calculée depuis resultats_humain)
# =============================================================================
class OperationStats(Base):
    """VIEW des statistiques agrégées par opération.

    Cette classe mappe la VIEW PostgreSQL operations_stats.
    Les données sont calculées automatiquement depuis resultats_humain.
    LECTURE SEULE - pas de create/update/delete.
    """

    __tablename__ = "operations_stats"

    operation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_decedes: Mapped[int] = mapped_column(Integer)
    nombre_disparus: Mapped[int] = mapped_column(Integer)
    nombre_blesses: Mapped[int] = mapped_column(Integer)
    nombre_sauves: Mapped[int] = mapped_column(Integer)
    nombre_impliques: Mapped[int] = mapped_column(Integer)
    nombre_assistances: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"<OperationStats op={self.operation_id}>"


# =============================================================================
# Table Users
# =============================================================================
class User(Base):
    """Utilisateurs de l'application Streamlit."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


# =============================================================================
# Table Audit Log (lecture seule)
# =============================================================================
class AuditLog(Base):
    """Journal d'audit - Alimenté par les triggers PostgreSQL.

    Cette table est en lecture seule depuis l'application.
    Les triggers INSERT/UPDATE/DELETE sur les autres tables
    alimentent automatiquement ce journal.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(10), nullable=False)
    record_id: Mapped[Optional[int]] = mapped_column(Integer)
    old_values = mapped_column(JSONB)
    new_values = mapped_column(JSONB)
    changed_fields = mapped_column(ARRAY(Text))
    user_id: Mapped[Optional[str]] = mapped_column(String(50))
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} - {self.table_name} {self.operation_type}>"

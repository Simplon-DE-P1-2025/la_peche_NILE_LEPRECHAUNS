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

    # Clé primaire
    operation_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identification
    numero_sitrep: Mapped[Optional[str]] = mapped_column(String(50))
    cross_sitrep: Mapped[Optional[str]] = mapped_column(String(100))
    date_operation: Mapped[Optional[date]] = mapped_column(Date)
    heure_operation: Mapped[Optional[time]] = mapped_column(Time)
    type_operation: Mapped[Optional[str]] = mapped_column(String(100))
    sous_type_operation: Mapped[Optional[str]] = mapped_column(String(100))

    # Alerte SECMAR
    pourquoi_alerte: Mapped[Optional[str]] = mapped_column(String(100))
    moyen_alerte: Mapped[Optional[str]] = mapped_column(String(100))
    qui_alerte: Mapped[Optional[str]] = mapped_column(String(100))
    categorie_qui_alerte: Mapped[Optional[str]] = mapped_column(String(100))

    # Localisation
    cross: Mapped[Optional[str]] = mapped_column(String(50))
    departement: Mapped[Optional[str]] = mapped_column(String(3))
    est_metropolitain: Mapped[Optional[bool]] = mapped_column(Boolean)
    zone_responsabilite: Mapped[Optional[str]] = mapped_column(String(50))
    latitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 6))
    longitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 6))

    # Contexte opération SECMAR
    evenement: Mapped[Optional[str]] = mapped_column(String(100))
    categorie_evenement: Mapped[Optional[str]] = mapped_column(String(100))
    autorite: Mapped[Optional[str]] = mapped_column(String(100))
    seconde_autorite: Mapped[Optional[str]] = mapped_column(String(100))

    # Conditions météo
    vent_direction: Mapped[Optional[int]] = mapped_column(Integer)
    vent_direction_categorie: Mapped[Optional[str]] = mapped_column(String(50))
    vent_force: Mapped[Optional[int]] = mapped_column(Integer)
    mer_force: Mapped[Optional[int]] = mapped_column(Integer)

    # Temporel SECMAR
    date_heure_reception_alerte: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    date_heure_fin_operation: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    fuseau_horaire: Mapped[Optional[str]] = mapped_column(String(50))
    systeme_source: Mapped[Optional[str]] = mapped_column(String(50))

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

    def to_dict(self) -> dict:
        """Convertir en dictionnaire."""
        return {
            "operation_id": self.operation_id,
            "numero_sitrep": self.numero_sitrep,
            "cross_sitrep": self.cross_sitrep,
            "date_operation": str(self.date_operation) if self.date_operation else None,
            "type_operation": self.type_operation,
            "cross": self.cross,
            "departement": self.departement,
            "est_metropolitain": self.est_metropolitain,
            "latitude": float(self.latitude) if self.latitude else None,
            "longitude": float(self.longitude) if self.longitude else None,
            "evenement": self.evenement,
            "categorie_evenement": self.categorie_evenement,
            "autorite": self.autorite,
            "prefecture_maritime": self.prefecture_maritime,
        }

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

    type_flotteur: Mapped[Optional[str]] = mapped_column(String(100))
    categorie_flotteur: Mapped[Optional[str]] = mapped_column(String(100))
    pavillon: Mapped[Optional[str]] = mapped_column(String(50))
    immatriculation: Mapped[Optional[str]] = mapped_column(String(50))
    resultat_flotteur: Mapped[Optional[str]] = mapped_column(String(100))

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

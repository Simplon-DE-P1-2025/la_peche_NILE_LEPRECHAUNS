"""Schema Pandera pour les Operations.

Validation partagee entre ETL et CRUD.

Usage:
    # Validation DataFrame (ETL)
    validated_df = OperationSchema.validate(df)

    # Validation avec factory (mode configurable)
    schema = create_operation_schema(enum_mode=ValidationMode.WARNING)
    validated_df = schema.validate(df)
"""

from typing import Optional

import pandera as pa
from pandera import Column, Check, DataFrameSchema
from pandera.typing import Series

from src.database.enums import (
    TYPE_OPERATION,
    CROSS_VALUES,
    PHASE_JOURNEE,
    MAREE_CATEGORIE,
    PREFECTURE_MARITIME,
)
from src.validation.base import (
    ValidationMode,
    create_enum_column,
)


class OperationSchema(pa.DataFrameModel):
    """Schema Pandera pour la table operations.

    Utilise pa.DataFrameModel pour une syntaxe declarative.
    Les enums sont valides en mode WARNING par defaut via create_operation_schema().
    """

    # Identification
    operation_id: Series[int] = pa.Field(ge=1, coerce=True)
    numero_sitrep: Optional[Series[str]] = pa.Field(nullable=True)
    cross_sitrep: Optional[Series[str]] = pa.Field(nullable=True)
    type_operation: Optional[Series[str]] = pa.Field(nullable=True)
    sous_type_operation: Optional[Series[str]] = pa.Field(nullable=True)

    # Alerte SECMAR
    pourquoi_alerte: Optional[Series[str]] = pa.Field(nullable=True)
    moyen_alerte: Optional[Series[str]] = pa.Field(nullable=True)
    qui_alerte: Optional[Series[str]] = pa.Field(nullable=True)
    categorie_qui_alerte: Optional[Series[str]] = pa.Field(nullable=True)

    # Localisation
    cross: Optional[Series[str]] = pa.Field(nullable=True)
    departement: Optional[Series[str]] = pa.Field(nullable=True)
    est_metropolitain: Optional[Series[bool]] = pa.Field(nullable=True, coerce=True)
    zone_responsabilite: Optional[Series[str]] = pa.Field(nullable=True)
    latitude: Optional[Series[float]] = pa.Field(
        nullable=True, ge=-90.0, le=90.0, coerce=True
    )
    longitude: Optional[Series[float]] = pa.Field(
        nullable=True, ge=-180.0, le=180.0, coerce=True
    )

    # Contexte operation SECMAR
    evenement: Optional[Series[str]] = pa.Field(nullable=True)
    categorie_evenement: Optional[Series[str]] = pa.Field(nullable=True)
    autorite: Optional[Series[str]] = pa.Field(nullable=True)
    seconde_autorite: Optional[Series[str]] = pa.Field(nullable=True)

    # Meteo
    vent_direction: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=360, coerce=True
    )
    vent_direction_categorie: Optional[Series[str]] = pa.Field(nullable=True)
    vent_force: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=12, coerce=True
    )  # Beaufort
    mer_force: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=9, coerce=True
    )  # Douglas

    # Temporel SECMAR
    date_heure_reception_alerte: Optional[Series[pa.DateTime]] = pa.Field(
        nullable=True, coerce=True
    )
    date_heure_fin_operation: Optional[Series[pa.DateTime]] = pa.Field(
        nullable=True, coerce=True
    )
    fuseau_horaire: Optional[Series[str]] = pa.Field(nullable=True)
    systeme_source: Optional[Series[str]] = pa.Field(nullable=True)

    # Enrichissement MCD
    est_jour_ferie: Optional[Series[bool]] = pa.Field(nullable=True, coerce=True)
    est_vacances_scolaires: Optional[Series[bool]] = pa.Field(nullable=True, coerce=True)
    phase_journee: Optional[Series[str]] = pa.Field(nullable=True)
    concerne_plongee: Optional[Series[bool]] = pa.Field(nullable=True, coerce=True)
    implique_wingfoil: Optional[Series[bool]] = pa.Field(nullable=True, coerce=True)
    distance_cote_metres: Optional[Series[float]] = pa.Field(
        nullable=True, ge=0, coerce=True
    )
    distance_cote_milles_nautiques: Optional[Series[float]] = pa.Field(
        nullable=True, ge=0, coerce=True
    )
    est_dans_stm: Optional[Series[bool]] = pa.Field(nullable=True, coerce=True)
    nom_stm: Optional[Series[str]] = pa.Field(nullable=True)
    est_dans_dst: Optional[Series[bool]] = pa.Field(nullable=True, coerce=True)
    nom_dst: Optional[Series[str]] = pa.Field(nullable=True)
    prefecture_maritime: Optional[Series[str]] = pa.Field(nullable=True)
    maree_port: Optional[Series[str]] = pa.Field(nullable=True)
    maree_coefficient: Optional[Series[int]] = pa.Field(
        nullable=True, ge=20, le=120, coerce=True
    )
    maree_categorie: Optional[Series[str]] = pa.Field(nullable=True)

    class Config:
        """Configuration du schema."""

        strict = False  # Autoriser colonnes supplementaires
        coerce = True  # Coercer les types automatiquement

    @pa.dataframe_check
    def coordinates_consistency(cls, df: pa.typing.DataFrame) -> Series[bool]:
        """Latitude et longitude doivent etre fournies ensemble ou absentes."""
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return True

        lat_null = df["latitude"].isna()
        lon_null = df["longitude"].isna()
        # Les deux doivent etre null ou non-null ensemble
        return lat_null == lon_null


def create_operation_schema(
    enum_mode: ValidationMode = ValidationMode.WARNING,
) -> DataFrameSchema:
    """Factory pour creer un schema Operation avec le mode enum configure.

    Args:
        enum_mode: STRICT (erreur) ou WARNING (signalement) pour les enums

    Returns:
        DataFrameSchema configure pour validation
    """
    return DataFrameSchema(
        columns={
            # Identification
            "operation_id": Column(pa.Int, Check.ge(1), coerce=True),
            "numero_sitrep": Column(pa.String, nullable=True, coerce=True),
            "cross_sitrep": Column(pa.String, nullable=True, coerce=True),
            "type_operation": create_enum_column(
                "type_operation",
                TYPE_OPERATION,
                mode=enum_mode,
                nullable=True,
            ),
            "sous_type_operation": Column(pa.String, nullable=True, coerce=True),
            # Alerte SECMAR
            "pourquoi_alerte": Column(pa.String, nullable=True, coerce=True),
            "moyen_alerte": Column(pa.String, nullable=True, coerce=True),
            "qui_alerte": Column(pa.String, nullable=True, coerce=True),
            "categorie_qui_alerte": Column(pa.String, nullable=True, coerce=True),
            # Localisation
            "cross": create_enum_column(
                "cross",
                CROSS_VALUES,
                mode=enum_mode,
                nullable=True,
            ),
            "departement": Column(pa.String, nullable=True, coerce=True),
            "est_metropolitain": Column(pa.Bool, nullable=True, coerce=True),
            "zone_responsabilite": Column(pa.String, nullable=True, coerce=True),
            "latitude": Column(
                pa.Float, Check.in_range(-90, 90), nullable=True, coerce=True
            ),
            "longitude": Column(
                pa.Float, Check.in_range(-180, 180), nullable=True, coerce=True
            ),
            # Contexte operation SECMAR
            "evenement": Column(pa.String, nullable=True, coerce=True),
            "categorie_evenement": Column(pa.String, nullable=True, coerce=True),
            "autorite": Column(pa.String, nullable=True, coerce=True),
            "seconde_autorite": Column(pa.String, nullable=True, coerce=True),
            # Meteo
            "vent_direction": Column(
                pa.Int, Check.in_range(0, 360), nullable=True, coerce=True
            ),
            "vent_direction_categorie": Column(pa.String, nullable=True, coerce=True),
            "vent_force": Column(
                pa.Int, Check.in_range(0, 12), nullable=True, coerce=True
            ),
            "mer_force": Column(
                pa.Int, Check.in_range(0, 9), nullable=True, coerce=True
            ),
            # Temporel SECMAR
            "date_heure_reception_alerte": Column(
                pa.DateTime, nullable=True, coerce=True
            ),
            "date_heure_fin_operation": Column(pa.DateTime, nullable=True, coerce=True),
            "fuseau_horaire": Column(pa.String, nullable=True, coerce=True),
            "systeme_source": Column(pa.String, nullable=True, coerce=True),
            # Enrichissement MCD
            "est_jour_ferie": Column(pa.Bool, nullable=True, coerce=True),
            "est_vacances_scolaires": Column(pa.Bool, nullable=True, coerce=True),
            "phase_journee": create_enum_column(
                "phase_journee", PHASE_JOURNEE, mode=enum_mode, nullable=True
            ),
            "concerne_plongee": Column(pa.Bool, nullable=True, coerce=True),
            "implique_wingfoil": Column(pa.Bool, nullable=True, coerce=True),
            "distance_cote_metres": Column(
                pa.Float, Check.ge(0), nullable=True, coerce=True
            ),
            "distance_cote_milles_nautiques": Column(
                pa.Float, Check.ge(0), nullable=True, coerce=True
            ),
            "est_dans_stm": Column(pa.Bool, nullable=True, coerce=True),
            "nom_stm": Column(pa.String, nullable=True, coerce=True),
            "est_dans_dst": Column(pa.Bool, nullable=True, coerce=True),
            "nom_dst": Column(pa.String, nullable=True, coerce=True),
            "prefecture_maritime": create_enum_column(
                "prefecture_maritime", PREFECTURE_MARITIME, mode=enum_mode, nullable=True
            ),
            "maree_port": Column(pa.String, nullable=True, coerce=True),
            "maree_coefficient": Column(
                pa.Int, Check.in_range(20, 120), nullable=True, coerce=True
            ),
            "maree_categorie": create_enum_column(
                "maree_categorie", MAREE_CATEGORIE, mode=enum_mode, nullable=True
            ),
        },
        checks=[
            # Check cross-field: lat/lon ensemble
            Check(
                lambda df: (
                    df["latitude"].isna() == df["longitude"].isna()
                    if "latitude" in df.columns and "longitude" in df.columns
                    else True
                ),
                name="coordinates_consistency",
                error="Latitude et longitude doivent etre fournies ensemble",
            ),
        ],
        strict=False,
        coerce=True,
    )

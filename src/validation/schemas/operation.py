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

from src.database.enums import TYPE_OPERATION, CROSS_VALUES
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
    date_operation: Optional[Series[pa.DateTime]] = pa.Field(nullable=True, coerce=True)
    heure_operation: Optional[Series[str]] = pa.Field(nullable=True)
    type_operation: Optional[Series[str]] = pa.Field(nullable=True)
    sous_type_operation: Optional[Series[str]] = pa.Field(nullable=True)
    cross: Optional[Series[str]] = pa.Field(nullable=True)

    # Localisation
    departement: Optional[Series[str]] = pa.Field(nullable=True)
    zone_responsabilite: Optional[Series[str]] = pa.Field(nullable=True)
    latitude: Optional[Series[float]] = pa.Field(
        nullable=True, ge=-90.0, le=90.0, coerce=True
    )
    longitude: Optional[Series[float]] = pa.Field(
        nullable=True, ge=-180.0, le=180.0, coerce=True
    )

    # Meteo
    vent_direction: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=360, coerce=True
    )
    vent_force: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=12, coerce=True
    )  # Beaufort
    mer_force: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, le=9, coerce=True
    )  # Douglas
    meteo: Optional[Series[str]] = pa.Field(nullable=True)

    # Bilan
    nombre_personnes_impliquees: Series[int] = pa.Field(ge=0, coerce=True, default=0)
    nombre_moyens_engages: Series[int] = pa.Field(ge=0, coerce=True, default=0)
    duree_intervention: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, coerce=True
    )

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
            "date_operation": Column(pa.DateTime, nullable=True, coerce=True),
            "heure_operation": Column(pa.String, nullable=True, coerce=True),
            "type_operation": create_enum_column(
                "type_operation",
                TYPE_OPERATION,
                mode=enum_mode,
                nullable=True,
            ),
            "sous_type_operation": Column(pa.String, nullable=True, coerce=True),
            "cross": create_enum_column(
                "cross",
                CROSS_VALUES,
                mode=enum_mode,
                nullable=True,
            ),
            # Localisation
            "departement": Column(pa.String, nullable=True, coerce=True),
            "zone_responsabilite": Column(pa.String, nullable=True, coerce=True),
            "latitude": Column(
                pa.Float, Check.in_range(-90, 90), nullable=True, coerce=True
            ),
            "longitude": Column(
                pa.Float, Check.in_range(-180, 180), nullable=True, coerce=True
            ),
            # Meteo
            "vent_direction": Column(
                pa.Int, Check.in_range(0, 360), nullable=True, coerce=True
            ),
            "vent_force": Column(
                pa.Int, Check.in_range(0, 12), nullable=True, coerce=True
            ),
            "mer_force": Column(
                pa.Int, Check.in_range(0, 9), nullable=True, coerce=True
            ),
            "meteo": Column(pa.String, nullable=True, coerce=True),
            # Bilan
            "nombre_personnes_impliquees": Column(
                pa.Int, Check.ge(0), coerce=True, default=0
            ),
            "nombre_moyens_engages": Column(pa.Int, Check.ge(0), coerce=True, default=0),
            "duree_intervention": Column(
                pa.Int, Check.ge(0), nullable=True, coerce=True
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

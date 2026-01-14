"""Schema Pandera pour les Flotteurs.

Validation partagee entre ETL et CRUD.
"""

from typing import Optional

import pandera as pa
from pandera import Column, Check, DataFrameSchema
from pandera.typing import Series

from src.database.enums import TYPE_FLOTTEUR, RESULTAT_FLOTTEUR
from src.validation.base import (
    ValidationMode,
    create_enum_column,
)


class FlotteurSchema(pa.DataFrameModel):
    """Schema Pandera pour la table flotteurs."""

    # Identification
    flotteur_id: Series[int] = pa.Field(ge=1, coerce=True)
    operation_id: Series[int] = pa.Field(ge=1, coerce=True)
    numero_ordre: Optional[Series[int]] = pa.Field(nullable=True, coerce=True)

    # Caracteristiques
    type_flotteur: Optional[Series[str]] = pa.Field(nullable=True)
    categorie_flotteur: Optional[Series[str]] = pa.Field(nullable=True)
    pavillon: Optional[Series[str]] = pa.Field(nullable=True)
    numero_immatriculation: Optional[Series[str]] = pa.Field(nullable=True)

    # Resultat
    resultat_flotteur: Optional[Series[str]] = pa.Field(nullable=True)

    class Config:
        """Configuration du schema."""

        strict = False
        coerce = True


def create_flotteur_schema(
    enum_mode: ValidationMode = ValidationMode.WARNING,
) -> DataFrameSchema:
    """Factory pour creer un schema Flotteur avec le mode enum configure.

    Args:
        enum_mode: STRICT (erreur) ou WARNING (signalement) pour les enums

    Returns:
        DataFrameSchema configure pour validation
    """
    return DataFrameSchema(
        columns={
            # Identification
            "flotteur_id": Column(pa.Int, Check.ge(1), coerce=True),
            "operation_id": Column(pa.Int, Check.ge(1), coerce=True),
            "numero_ordre": Column(pa.Int, nullable=True, coerce=True),
            # Caracteristiques
            "type_flotteur": create_enum_column(
                "type_flotteur",
                TYPE_FLOTTEUR,
                mode=enum_mode,
                nullable=True,
            ),
            "categorie_flotteur": Column(pa.String, nullable=True, coerce=True),
            "pavillon": Column(pa.String, nullable=True, coerce=True),
            "numero_immatriculation": Column(pa.String, nullable=True, coerce=True),
            # Resultat
            "resultat_flotteur": create_enum_column(
                "resultat_flotteur",
                RESULTAT_FLOTTEUR,
                mode=enum_mode,
                nullable=True,
            ),
        },
        strict=False,
        coerce=True,
    )

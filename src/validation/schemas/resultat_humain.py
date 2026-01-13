"""Schema Pandera pour les Resultats Humains.

Validation partagee entre ETL et CRUD.
"""

from typing import Optional

import pandera as pa
from pandera import Column, Check, DataFrameSchema
from pandera.typing import Series

from src.database.enums import RESULTAT_HUMAIN, CATEGORIE_PERSONNE
from src.validation.base import (
    ValidationMode,
    create_enum_column,
)


class ResultatHumainSchema(pa.DataFrameModel):
    """Schema Pandera pour la table resultats_humains."""

    # Identification
    resultat_id: Series[int] = pa.Field(ge=1, coerce=True)
    operation_id: Series[int] = pa.Field(ge=1, coerce=True)

    # Informations
    categorie_personne: Optional[Series[str]] = pa.Field(nullable=True)
    resultat_humain: Optional[Series[str]] = pa.Field(nullable=True)
    nombre: Series[int] = pa.Field(ge=1, coerce=True)

    class Config:
        """Configuration du schema."""

        strict = False
        coerce = True

    @pa.dataframe_check
    def resultat_nombre_coherence(cls, df: pa.typing.DataFrame) -> Series[bool]:
        """Si un resultat est specifie, le nombre doit etre >= 1."""
        if "resultat_humain" not in df.columns or "nombre" not in df.columns:
            return True

        # Si resultat_humain est non-null et non-vide, nombre doit etre >= 1
        has_resultat = df["resultat_humain"].notna() & (df["resultat_humain"] != "")
        has_nombre = df["nombre"] >= 1

        # Condition: pas de resultat OU nombre >= 1
        return ~has_resultat | has_nombre


def create_resultat_humain_schema(
    enum_mode: ValidationMode = ValidationMode.WARNING,
) -> DataFrameSchema:
    """Factory pour creer un schema ResultatHumain avec le mode enum configure.

    Args:
        enum_mode: STRICT (erreur) ou WARNING (signalement) pour les enums

    Returns:
        DataFrameSchema configure pour validation
    """
    return DataFrameSchema(
        columns={
            # Identification
            "resultat_id": Column(pa.Int, Check.ge(1), coerce=True),
            "operation_id": Column(pa.Int, Check.ge(1), coerce=True),
            # Informations
            "categorie_personne": create_enum_column(
                "categorie_personne",
                CATEGORIE_PERSONNE,
                mode=enum_mode,
                nullable=True,
            ),
            "resultat_humain": create_enum_column(
                "resultat_humain",
                RESULTAT_HUMAIN,
                mode=enum_mode,
                nullable=True,
            ),
            "nombre": Column(pa.Int, Check.ge(1), coerce=True),
        },
        checks=[
            # Check coherence resultat/nombre
            Check(
                lambda df: _check_resultat_nombre(df),
                name="resultat_nombre_coherence",
                error="Un resultat humain doit avoir un nombre de personnes >= 1",
            ),
        ],
        strict=False,
        coerce=True,
    )


def _check_resultat_nombre(df: pa.typing.DataFrame) -> bool:
    """Verifie que si un resultat est specifie, nombre >= 1."""
    if "resultat_humain" not in df.columns or "nombre" not in df.columns:
        return True

    has_resultat = df["resultat_humain"].notna() & (df["resultat_humain"] != "")
    has_nombre = df["nombre"] >= 1

    return (~has_resultat | has_nombre).all()

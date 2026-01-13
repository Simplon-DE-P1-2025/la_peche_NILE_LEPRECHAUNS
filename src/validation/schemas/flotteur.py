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


# Limites de longueur coherentes par type de flotteur
TYPE_MAX_LONGUEUR = {
    "Canoe/Kayak": 6.0,
    "Jet-ski": 5.0,
    "Planche a voile": 5.0,
    "Kitesurf": 3.0,
    "Engin de plage": 4.0,
    "Ski nautique": 3.0,
}


class FlotteurSchema(pa.DataFrameModel):
    """Schema Pandera pour la table flotteurs."""

    # Identification
    flotteur_id: Series[int] = pa.Field(ge=1, coerce=True)
    operation_id: Series[int] = pa.Field(ge=1, coerce=True)

    # Caracteristiques
    type_flotteur: Optional[Series[str]] = pa.Field(nullable=True)
    categorie_flotteur: Optional[Series[str]] = pa.Field(nullable=True)
    pavillon: Optional[Series[str]] = pa.Field(nullable=True)
    immatriculation: Optional[Series[str]] = pa.Field(nullable=True)
    nom_flotteur: Optional[Series[str]] = pa.Field(nullable=True)
    longueur: Optional[Series[float]] = pa.Field(nullable=True, ge=0, coerce=True)

    # Bilan
    nombre_personnes: Optional[Series[int]] = pa.Field(
        nullable=True, ge=0, coerce=True
    )
    resultat_flotteur: Optional[Series[str]] = pa.Field(nullable=True)

    class Config:
        """Configuration du schema."""

        strict = False
        coerce = True

    @pa.dataframe_check
    def longueur_type_coherence(cls, df: pa.typing.DataFrame) -> Series[bool]:
        """Verifie la coherence longueur/type (ex: kayak != 50m)."""
        if "type_flotteur" not in df.columns or "longueur" not in df.columns:
            return True

        results = [True] * len(df)

        for idx, row in df.iterrows():
            type_f = row.get("type_flotteur")
            longueur = row.get("longueur")

            if type_f and longueur and type_f in TYPE_MAX_LONGUEUR:
                max_len = TYPE_MAX_LONGUEUR[type_f]
                if longueur > max_len:
                    results[idx] = False

        return pa.typing.Series[bool](results, index=df.index)


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
            # Caracteristiques
            "type_flotteur": create_enum_column(
                "type_flotteur",
                TYPE_FLOTTEUR,
                mode=enum_mode,
                nullable=True,
            ),
            "categorie_flotteur": Column(pa.String, nullable=True, coerce=True),
            "pavillon": Column(pa.String, nullable=True, coerce=True),
            "immatriculation": Column(pa.String, nullable=True, coerce=True),
            "nom_flotteur": Column(pa.String, nullable=True, coerce=True),
            "longueur": Column(pa.Float, Check.ge(0), nullable=True, coerce=True),
            # Bilan
            "nombre_personnes": Column(pa.Int, Check.ge(0), nullable=True, coerce=True),
            "resultat_flotteur": create_enum_column(
                "resultat_flotteur",
                RESULTAT_FLOTTEUR,
                mode=enum_mode,
                nullable=True,
            ),
        },
        checks=[
            # Check coherence type/longueur
            Check(
                lambda df: _check_longueur_type(df),
                name="longueur_type_coherence",
                error="Longueur incoherente avec le type de flotteur",
            ),
        ],
        strict=False,
        coerce=True,
    )


def _check_longueur_type(df: pa.typing.DataFrame) -> bool:
    """Verifie la coherence longueur/type pour tous les enregistrements."""
    if "type_flotteur" not in df.columns or "longueur" not in df.columns:
        return True

    for _, row in df.iterrows():
        type_f = row.get("type_flotteur")
        longueur = row.get("longueur")

        if type_f and longueur and type_f in TYPE_MAX_LONGUEUR:
            max_len = TYPE_MAX_LONGUEUR[type_f]
            if longueur > max_len:
                return False

    return True

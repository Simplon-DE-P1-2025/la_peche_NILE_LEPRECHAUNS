"""Schemas Pandera pour les entites SECMAR.

Usage:
    from src.validation.schemas import OperationSchema, FlotteurSchema, ResultatHumainSchema

    # Validation DataFrame (ETL)
    validated_df = OperationSchema.validate(df)

    # Validation dict (CRUD) - via integration.py
    from src.validation import validate_for_crud
"""

from src.validation.schemas.operation import OperationSchema
from src.validation.schemas.flotteur import FlotteurSchema
from src.validation.schemas.resultat_humain import ResultatHumainSchema

__all__ = [
    "OperationSchema",
    "FlotteurSchema",
    "ResultatHumainSchema",
]

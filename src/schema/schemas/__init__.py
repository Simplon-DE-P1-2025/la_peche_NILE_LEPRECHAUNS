"""Schemas des entites de l'application.

Ce module exporte les schemas de toutes les entites:
- OPERATION_SCHEMA: Operations de sauvetage maritime
- FLOTTEUR_SCHEMA: Embarcations impliquees
- RESULTAT_HUMAIN_SCHEMA: Bilans humains

Usage:
    from src.schema.schemas import OPERATION_SCHEMA, FLOTTEUR_SCHEMA
"""

from src.schema.schemas.operation import OPERATION_SCHEMA
from src.schema.schemas.flotteur import FLOTTEUR_SCHEMA
from src.schema.schemas.resultat_humain import RESULTAT_HUMAIN_SCHEMA

__all__ = [
    "OPERATION_SCHEMA",
    "FLOTTEUR_SCHEMA",
    "RESULTAT_HUMAIN_SCHEMA",
]

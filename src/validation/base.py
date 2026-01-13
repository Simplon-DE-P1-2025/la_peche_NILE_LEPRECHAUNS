"""Classes de base pour validation Pandera.

Fournit les utilitaires pour creer des schemas partages entre ETL et CRUD.

Usage:
    from src.validation.base import ValidationMode, ValidationResult, create_enum_column

    # Mode WARNING pour enums (signalement sans blocage)
    column = create_enum_column("type_operation", TYPE_OPERATION, ValidationMode.WARNING)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

import pandas as pd
import pandera as pa
from pandera import Column, Check


class ValidationMode(Enum):
    """Modes de validation pour les enums."""

    STRICT = "strict"  # Erreur si valeur hors enum
    WARNING = "warning"  # Warning seulement, pas de blocage


@dataclass
class ValidationResult:
    """Resultat de validation avec warnings separes des erreurs.

    Attributes:
        is_valid: True si aucune erreur bloquante
        errors: Liste des erreurs bloquantes
        warnings: Liste des warnings non bloquants (ex: enum non standard)
        validated_data: DataFrame valide (si is_valid=True)
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_data: Optional[pd.DataFrame] = None


class EnumWarningCollector:
    """Collecteur de warnings pour valeurs enum non standard.

    Utilise pour le mode WARNING : ne bloque pas la validation
    mais collecte les valeurs hors liste pour affichage UI.
    """

    def __init__(self) -> None:
        self._warnings: List[str] = []

    @property
    def warnings(self) -> List[str]:
        """Retourne les warnings collectes."""
        return self._warnings.copy()

    def clear(self) -> None:
        """Reinitialise les warnings."""
        self._warnings.clear()

    def check_enum(
        self,
        series: pd.Series,
        allowed_values: List[Any],
        field_name: str,
        field_label: str,
    ) -> None:
        """Verifie les valeurs et collecte les warnings.

        Args:
            series: Serie pandas a verifier
            allowed_values: Liste des valeurs autorisees
            field_name: Nom technique du champ
            field_label: Label affiche pour les messages
        """
        allowed_set = set(allowed_values)

        # Trouver les valeurs non-null qui ne sont pas dans la liste
        mask = series.notna() & (series != "") & (~series.isin(allowed_set))
        invalid_values = series[mask].unique()

        for val in invalid_values:
            preview = ", ".join(str(v) for v in sorted(allowed_values)[:5])
            self._warnings.append(
                f"Valeur '{val}' non standard pour '{field_label}'. "
                f"Valeurs connues: {preview}..."
            )


def create_enum_check_warning(
    allowed_values: List[Any],
    field_name: str,
) -> Check:
    """Cree un Check Pandera pour enum en mode WARNING.

    Le check retourne toujours True (pas de blocage).
    Les valeurs hors liste sont signalees via logs.

    Args:
        allowed_values: Liste des valeurs autorisees
        field_name: Nom du champ pour les messages

    Returns:
        Check Pandera qui ne bloque jamais
    """
    allowed_set = set(allowed_values)

    def check_fn(series: pd.Series) -> pd.Series:
        # Toujours retourner True - pas de blocage en mode WARNING
        # Le signalement est fait via EnumWarningCollector dans integration.py
        return pd.Series([True] * len(series), index=series.index)

    return Check(
        check_fn,
        element_wise=False,
        name=f"enum_warning_{field_name}",
        error=f"Valeur non standard pour {field_name} (warning uniquement)",
    )


def create_enum_column(
    field_name: str,
    allowed_values: List[Any],
    mode: ValidationMode = ValidationMode.WARNING,
    nullable: bool = True,
    **kwargs: Any,
) -> Column:
    """Cree une colonne Pandera avec validation enum configurable.

    Args:
        field_name: Nom du champ pour les messages
        allowed_values: Liste des valeurs autorisees
        mode: STRICT (erreur) ou WARNING (signalement)
        nullable: Autoriser les valeurs nulles
        **kwargs: Arguments supplementaires pour Column

    Returns:
        Column Pandera configuree
    """
    if mode == ValidationMode.STRICT:
        return Column(
            pa.String,
            checks=Check.isin(allowed_values),
            nullable=nullable,
            coerce=True,
            **kwargs,
        )
    else:
        # Mode WARNING : check qui ne bloque jamais
        return Column(
            pa.String,
            checks=create_enum_check_warning(allowed_values, field_name),
            nullable=nullable,
            coerce=True,
            **kwargs,
        )

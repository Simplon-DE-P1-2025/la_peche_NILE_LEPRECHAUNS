"""Integration Pandera avec le systeme existant.

Pont entre:
- FieldSchema (UI) et Pandera Column (validation)
- FormGenerator.validate() et Pandera
- CRUD operations et validation

Usage:
    from src.validation.integration import validate_for_crud
    from src.schema.schemas import OPERATION_SCHEMA

    result = validate_for_crud(OPERATION_SCHEMA, form_data)
    if not result.is_valid:
        for error in result.errors:
            st.error(error)
    for warning in result.warnings:
        st.warning(warning)
"""

from typing import Any, Dict, List, Optional, Set
import re

import pandas as pd
import pandera as pa
from pandera import Column, Check, DataFrameSchema

from src.schema.definitions import FieldSchema, EntitySchema, WidgetType
from src.database import enums
from src.validation.base import (
    ValidationMode,
    ValidationResult,
    EnumWarningCollector,
)


def _format_error_french(
    error_str: str,
    entity_schema: EntitySchema,
    check_type: str = "",
    column_name: str = "",
    failure_value: Any = None,
) -> str:
    """Traduit les erreurs Pandera en messages francais avec labels.

    Args:
        error_str: Message d'erreur brut Pandera
        entity_schema: Schema pour recuperer les labels
        check_type: Type de check (ge, le, str_length, etc.)
        column_name: Nom de la colonne concernee
        failure_value: Valeur qui a echoue

    Returns:
        Message d'erreur en francais
    """
    # Map des noms de colonnes vers les labels
    field_map = {f.name: f for f in entity_schema.fields}

    # Si on a le nom de colonne, utiliser le label
    label = column_name
    field = field_map.get(column_name)
    if field:
        label = field.label

    check_lower = check_type.lower()

    # Traduire selon le type de check
    if "champ_requis" in check_lower or "required" in check_lower:
        return f"Le champ '{label}' est requis"

    if "greater_than_or_equal_to" in check_lower or "ge(" in check_lower:
        # Extraire la valeur min du check (format: greater_than_or_equal_to(90.0))
        match = re.search(r"[-]?(\d+\.?\d*)", str(check_type))
        min_val = match.group(0) if match else "?"
        return f"Le champ '{label}' doit etre >= {min_val}"

    if "less_than_or_equal_to" in check_lower or "le(" in check_lower:
        match = re.search(r"[-]?(\d+\.?\d*)", str(check_type))
        max_val = match.group(0) if match else "?"
        return f"Le champ '{label}' doit etre <= {max_val}"

    if "str_length" in check_lower:
        match = re.search(r"max_value=(\d+)", str(check_type))
        if not match:
            match = re.search(r"(\d+)", str(check_type))
        max_len = match.group(1) if match else "?"
        return f"Le champ '{label}' ne doit pas depasser {max_len} caracteres"

    if "not_nullable" in check_lower or "nullable" in error_str.lower():
        return f"Le champ '{label}' est requis"

    # Fallback: remplacer les noms techniques par les labels
    result = error_str
    for name, f in field_map.items():
        result = result.replace(f"'{name}'", f"'{f.label}'")
        result = result.replace(f"Column {name}", f"Champ {f.label}")
        result = result.replace(f"column '{name}'", f"champ '{f.label}'")

    return result


# Mapping WidgetType vers types Pandera
WIDGET_TO_PANDERA = {
    WidgetType.TEXT_INPUT: pa.String,
    WidgetType.TEXT_AREA: pa.String,
    WidgetType.NUMBER_INPUT: pa.Float,
    WidgetType.SELECTBOX: pa.String,
    WidgetType.MULTISELECT: pa.Object,
    WidgetType.DATE_INPUT: pa.DateTime,
    WidgetType.TIME_INPUT: pa.String,
    WidgetType.CHECKBOX: pa.Bool,
}


class SchemaConverter:
    """Convertit un EntitySchema en DataFrameSchema Pandera."""

    def __init__(
        self,
        entity_schema: EntitySchema,
        enum_mode: ValidationMode = ValidationMode.WARNING,
    ):
        """
        Args:
            entity_schema: Schema EntitySchema existant
            enum_mode: Mode pour les validations enum
        """
        self.entity_schema = entity_schema
        self.enum_mode = enum_mode
        self._pandera_schema: Optional[DataFrameSchema] = None
        self._enum_collector = EnumWarningCollector()

    def _field_to_column(self, field: FieldSchema) -> Column:
        """Convertit un FieldSchema en Column Pandera."""

        # Type de base
        base_type = WIDGET_TO_PANDERA.get(field.widget, pa.String)

        # Detecter si c'est un entier
        if field.widget == WidgetType.NUMBER_INPUT:
            if field.step and isinstance(field.step, int):
                base_type = pa.Int
            elif field.format_str and "d" in field.format_str:
                base_type = pa.Int

        checks = []

        # Check pour champs requis (None ET chaine vide)
        if field.required:
            # Capturer le label dans la closure
            field_label = field.label

            def make_required_check(label: str):
                def check_required(s: pd.Series) -> pd.Series:
                    # Verifier non-null et non-vide
                    is_valid = s.notna()
                    # Pour les strings, verifier aussi non-vide
                    str_mask = s.apply(lambda x: isinstance(x, str))
                    is_valid = is_valid & ~(str_mask & (s.astype(str).str.strip() == ""))
                    return is_valid

                return Check(
                    check_required,
                    name=f"champ_requis_{label}",
                    error=f"Le champ '{label}' est requis",
                )

            checks.append(make_required_check(field_label))

        # Min/Max pour nombres
        if field.min_value is not None:
            checks.append(Check.ge(field.min_value))
        if field.max_value is not None:
            checks.append(Check.le(field.max_value))

        # Longueur max pour strings
        if field.max_chars and field.widget in [
            WidgetType.TEXT_INPUT,
            WidgetType.TEXT_AREA,
        ]:
            checks.append(Check.str_length(max_value=field.max_chars))

        # Note: Les enums sont geres separement via _check_enum_warnings
        # en mode WARNING pour ne pas bloquer la validation

        return Column(
            base_type,
            checks=checks if checks else None,
            nullable=True,  # On gere required via le check custom
            coerce=True,
            required=False,  # Ne pas exiger la presence de la colonne
        )

    def build_schema(
        self, exclude_fields: Optional[Set[str]] = None
    ) -> DataFrameSchema:
        """Construit le DataFrameSchema Pandera.

        Args:
            exclude_fields: Champs a exclure de la validation

        Returns:
            DataFrameSchema Pandera
        """
        exclude_fields = exclude_fields or set()

        columns = {}
        for field in self.entity_schema.fields:
            # Ignorer les champs auto-generes ou timestamps
            if field.name in ["created_at", "updated_at"]:
                continue
            # Ignorer les champs exclus
            if field.name in exclude_fields:
                continue
            columns[field.name] = self._field_to_column(field)

        return DataFrameSchema(
            columns=columns,
            strict=False,  # Autoriser colonnes supplementaires
            coerce=True,
        )

    def _check_enum_warnings(self, data: Dict[str, Any]) -> List[str]:
        """Verifie les valeurs enum et genere des warnings.

        Args:
            data: Dictionnaire de donnees a verifier

        Returns:
            Liste des warnings pour valeurs non standard
        """
        self._enum_collector.clear()

        for field in self.entity_schema.fields:
            if field.enum_ref:
                value = data.get(field.name)
                if value is not None and value != "":
                    enum_values = getattr(enums, field.enum_ref, [])
                    if enum_values:
                        # Utiliser le collecteur pour un message uniforme
                        series = pd.Series([value])
                        self._enum_collector.check_enum(
                            series, enum_values, field.name, field.label
                        )

        return self._enum_collector.warnings

    def validate_dict(
        self,
        data: Dict[str, Any],
        exclude_fields: Optional[Set[str]] = None,
    ) -> ValidationResult:
        """Valide un dictionnaire (pour CRUD single record).

        Args:
            data: Dictionnaire de donnees
            exclude_fields: Champs a exclure de la validation

        Returns:
            ValidationResult avec errors et warnings
        """
        schema = self.build_schema(exclude_fields)

        # Filtrer les colonnes connues du schema
        known_columns = set(schema.columns.keys())
        filtered_data = {k: v for k, v in data.items() if k in known_columns}

        # Convertir en DataFrame single-row
        df = pd.DataFrame([filtered_data])

        errors: List[str] = []
        warnings: List[str] = []

        try:
            validated_df = schema.validate(df, lazy=True)

            # Collecter les warnings enum (mode WARNING)
            warnings.extend(self._check_enum_warnings(data))

            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=warnings,
                validated_data=validated_df,
            )
        except pa.errors.SchemaError as e:
            # Traduire l'erreur en francais
            error_msg = _format_error_french(str(e), self.entity_schema)
            errors.append(error_msg)
            # Collecter aussi les warnings meme en cas d'erreur
            warnings.extend(self._check_enum_warnings(data))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
            )
        except pa.errors.SchemaErrors as e:
            # Collecter toutes les erreurs en mode lazy avec traduction
            for failure_case in e.failure_cases.itertuples():
                check_str = str(failure_case.check)

                # Ignorer les erreurs purement techniques (coercion, dtype)
                if "coerce_dtype" in check_str or "dtype(" in check_str:
                    continue

                error_msg = _format_error_french(
                    check_str,
                    self.entity_schema,
                    check_type=check_str,
                    column_name=str(failure_case.column),
                    failure_value=failure_case.failure_case,
                )
                errors.append(error_msg)

            # Dedupliquer les erreurs (meme message possible plusieurs fois)
            errors = list(dict.fromkeys(errors))

            warnings.extend(self._check_enum_warnings(data))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
            )


def validate_for_crud(
    entity_schema: EntitySchema,
    data: Dict[str, Any],
    exclude_fields: Optional[Set[str]] = None,
    enum_mode: ValidationMode = ValidationMode.WARNING,
) -> ValidationResult:
    """Fonction utilitaire pour valider avant CRUD.

    Usage:
        from src.validation.integration import validate_for_crud
        from src.schema.schemas import OPERATION_SCHEMA

        result = validate_for_crud(OPERATION_SCHEMA, data_dict)
        if not result.is_valid:
            for error in result.errors:
                st.error(error)
        for warning in result.warnings:
            st.warning(warning)

    Args:
        entity_schema: Schema de l'entite (OPERATION_SCHEMA, etc.)
        data: Dictionnaire de donnees a valider
        exclude_fields: Champs a exclure de la validation
        enum_mode: STRICT ou WARNING pour les enums

    Returns:
        ValidationResult avec is_valid, errors, warnings
    """
    converter = SchemaConverter(entity_schema, enum_mode)
    return converter.validate_dict(data, exclude_fields)


def validate_dataframe(
    entity_schema: EntitySchema,
    df: pd.DataFrame,
    enum_mode: ValidationMode = ValidationMode.WARNING,
) -> ValidationResult:
    """Valide un DataFrame complet (pour ETL).

    Usage:
        from src.validation.integration import validate_dataframe
        from src.schema.schemas import OPERATION_SCHEMA

        result = validate_dataframe(OPERATION_SCHEMA, raw_df)
        if not result.is_valid:
            print(f"Erreurs: {result.errors}")
        validated_df = result.validated_data

    Args:
        entity_schema: Schema de l'entite
        df: DataFrame a valider
        enum_mode: STRICT ou WARNING pour les enums

    Returns:
        ValidationResult avec DataFrame valide si succes
    """
    converter = SchemaConverter(entity_schema, enum_mode)
    schema = converter.build_schema()

    errors: List[str] = []
    warnings: List[str] = []

    try:
        validated_df = schema.validate(df, lazy=True)

        # Collecter les warnings enum pour chaque ligne
        for _, row in df.iterrows():
            row_warnings = converter._check_enum_warnings(row.to_dict())
            warnings.extend(row_warnings)

        # Dedupliquer les warnings
        warnings = list(set(warnings))

        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            validated_data=validated_df,
        )
    except pa.errors.SchemaErrors as e:
        for failure_case in e.failure_cases.itertuples():
            error_msg = f"Ligne {failure_case.index}: {failure_case.column} - {failure_case.check}"
            errors.append(error_msg)

        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
        )

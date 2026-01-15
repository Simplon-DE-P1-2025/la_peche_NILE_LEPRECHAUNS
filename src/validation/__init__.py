"""Module de validation Pandera pour SECMAR.

Fournit des schemas de validation partages entre ETL et CRUD.

Architecture de validation (Defense en profondeur)
==================================================

L'application utilise DEUX couches de validation complementaires:

1. COUCHE UI (Streamlit widgets) - Validation immediate
   - st.number_input: enforce min_value/max_value
   - st.text_input: enforce max_chars
   - st.selectbox: limite aux options definies
   - Avantage: feedback instantane, empeche la saisie invalide
   - Fichier: src/schema/form_generator.py

2. COUCHE BACKEND (Pandera) - Validation de securite
   - Valide les donnees AVANT insertion en base
   - Attrape les cas non couverts par l'UI:
     * Champs requis vides (Streamlit ne bloque pas)
     * Import CSV/Excel (pas de widgets UI)
     * Appels API directs (contournent l'interface)
     * Validation cross-field future (ex: date_fin > date_debut)
   - Fichier: src/validation/integration.py

Pourquoi garder les deux?
-------------------------
- La validation UI est "gratuite" (fournie par Streamlit)
- Pandera ajoute une securite pour les flux non-UI
- Defense en profondeur = meilleure robustesse
- Cout de maintenance minimal (schemas partages)

Usage:
    # Validation pour CRUD (single record)
    from src.validation import validate_for_crud, ValidationMode
    from src.schema.schemas import OPERATION_SCHEMA

    result = validate_for_crud(OPERATION_SCHEMA, form_data)
    if not result.is_valid:
        for error in result.errors:
            st.error(error)
    for warning in result.warnings:
        st.warning(warning)  # Non bloquant

    # Validation pour ETL (DataFrame)
    from src.validation import validate_dataframe
    result = validate_dataframe(OPERATION_SCHEMA, raw_df)

    # Schemas Pandera directs (pour ETL avance)
    from src.validation.schemas import OperationSchema
    validated_df = OperationSchema.validate(df)
"""

from src.validation.base import (
    ValidationMode,
    ValidationResult,
    EnumWarningCollector,
    create_enum_column,
)

from src.validation.integration import (
    validate_for_crud,
    validate_dataframe,
    SchemaConverter,
)

from src.validation.schemas import (
    OperationSchema,
    FlotteurSchema,
    ResultatHumainSchema,
)

__all__ = [
    # Base
    "ValidationMode",
    "ValidationResult",
    "EnumWarningCollector",
    "create_enum_column",
    # Integration
    "validate_for_crud",
    "validate_dataframe",
    "SchemaConverter",
    # Schemas
    "OperationSchema",
    "FlotteurSchema",
    "ResultatHumainSchema",
]

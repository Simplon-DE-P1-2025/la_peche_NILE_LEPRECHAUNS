"""Page Catalogue de donnees - Dictionnaire de donnees interactif.

Cette page affiche:
- Navigation entre les 3 entites principales (Operation, Flotteur, ResultatHumain)
- Dictionnaire des champs avec types, descriptions SECMAR et contraintes
- Valeurs des enumerations
- Diagramme des relations entre entites

Auteur: Equipe Sprint 3-4
Date: Janvier 2026
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from typing import List, Dict, Any

# =============================================================================
# Configuration du path pour imports
# =============================================================================
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.schema.schemas import (
    OPERATION_SCHEMA,
    FLOTTEUR_SCHEMA,
    RESULTAT_HUMAIN_SCHEMA,
)
from src.schema.secmar_descriptions import SECMAR_DESCRIPTIONS
from src.schema.definitions import FieldSchema, WidgetType, EntitySchema
from src.database import enums
from src.database.connection import get_session
from src.database.crud import crud_operation, crud_flotteur, crud_resultat_humain


# =============================================================================
# Configuration de la page Streamlit
# =============================================================================
st.set_page_config(
    page_title="Catalogue SECMAR",
    page_icon="📚",
    layout="wide",
)


# =============================================================================
# Authentification
# =============================================================================
if not login_required():
    st.stop()

show_user_info()


# =============================================================================
# Fonctions utilitaires
# =============================================================================

# Mapping WidgetType -> Type affiche
WIDGET_TYPE_MAPPING = {
    WidgetType.TEXT_INPUT: "str",
    WidgetType.TEXT_AREA: "str",
    WidgetType.NUMBER_INPUT: "int/float",
    WidgetType.SELECTBOX: "enum",
    WidgetType.MULTISELECT: "list",
    WidgetType.DATE_INPUT: "datetime",
    WidgetType.TIME_INPUT: "time",
    WidgetType.CHECKBOX: "bool",
}


def get_field_metadata(field: FieldSchema) -> Dict[str, Any]:
    """Extraire les metadonnees d'un champ pour le catalogue.

    Args:
        field: Schema du champ

    Returns:
        Dictionnaire avec nom, type, description, contraintes, valeurs enum
    """
    # Type Python depuis le widget
    field_type = WIDGET_TYPE_MAPPING.get(field.widget, "str")

    # Description SECMAR (fallback sur help_text)
    description = SECMAR_DESCRIPTIONS.get(field.name, field.help_text or "-")

    # Contraintes
    constraints = []
    if field.required:
        constraints.append("Obligatoire")
    if field.min_value is not None:
        constraints.append(f"Min: {field.min_value}")
    if field.max_value is not None:
        constraints.append(f"Max: {field.max_value}")
    if field.max_chars is not None:
        constraints.append(f"Max {field.max_chars} car.")

    # Valeurs enum
    enum_values = []
    if field.enum_ref:
        enum_values = getattr(enums, field.enum_ref, [])

    return {
        "Champ": field.name,
        "Label": field.label,
        "Type": field_type,
        "Description": description,
        "Contraintes": ", ".join(constraints) if constraints else "-",
        "enum_ref": field.enum_ref,
        "enum_values": enum_values,
        "section": field.section,
    }


def build_dictionary_dataframe(schema: EntitySchema) -> pd.DataFrame:
    """Construit le DataFrame du dictionnaire pour une entite.

    Args:
        schema: Schema de l'entite

    Returns:
        DataFrame avec les colonnes du dictionnaire
    """
    data = []
    for field in schema.fields:
        meta = get_field_metadata(field)
        # Apercu des valeurs enum (3 premieres + ...)
        enum_preview = "-"
        if meta["enum_values"]:
            values = meta["enum_values"]
            if len(values) > 3:
                enum_preview = ", ".join(values[:3]) + "..."
            else:
                enum_preview = ", ".join(values)

        data.append({
            "Champ": meta["Champ"],
            "Label": meta["Label"],
            "Type": meta["Type"],
            "Description": meta["Description"],
            "Contraintes": meta["Contraintes"],
            "Valeurs enum": enum_preview,
        })

    return pd.DataFrame(data)


def get_enum_fields(schema: EntitySchema) -> List[FieldSchema]:
    """Retourne les champs avec enum_ref defini."""
    return [f for f in schema.fields if f.enum_ref]


# =============================================================================
# En-tete de la page
# =============================================================================
st.title("📚 Catalogue de Donnees")
st.caption("Dictionnaire de donnees SECMAR - Descriptions officielles")


# =============================================================================
# Section: Metriques globales
# =============================================================================
st.subheader("Vue d'ensemble")

col1, col2, col3 = st.columns(3)

try:
    with get_session() as session:
        with col1:
            count_ops = crud_operation.count(session)
            st.metric("Operations", f"{count_ops:,}".replace(",", " "))
        with col2:
            count_flot = crud_flotteur.count(session)
            st.metric("Flotteurs", f"{count_flot:,}".replace(",", " "))
        with col3:
            count_res = crud_resultat_humain.count(session)
            st.metric("Resultats Humains", f"{count_res:,}".replace(",", " "))
except Exception as e:
    st.warning(f"Impossible de charger les statistiques: {e}")

st.divider()


# =============================================================================
# Section: Dictionnaire par entite (Tabs)
# =============================================================================
tab_op, tab_flot, tab_res = st.tabs([
    "🚢 Operations",
    "⛵ Flotteurs",
    "👥 Resultats Humains",
])


# -----------------------------------------------------------------------------
# Tab: Operations
# -----------------------------------------------------------------------------
with tab_op:
    st.markdown(f"### {OPERATION_SCHEMA.display_name}")
    st.info(f"Entite principale - {len(OPERATION_SCHEMA.fields)} champs")

    # Tableau du dictionnaire
    df_op = build_dictionary_dataframe(OPERATION_SCHEMA)
    st.dataframe(df_op, use_container_width=True, hide_index=True, height=400)

    # Expander pour les valeurs d'enumeration
    enum_fields_op = get_enum_fields(OPERATION_SCHEMA)
    if enum_fields_op:
        with st.expander("📋 Valeurs des enumerations", expanded=False):
            for field in enum_fields_op:
                values = getattr(enums, field.enum_ref, [])
                st.markdown(f"**{field.label}** (`{field.enum_ref}`)")
                # Afficher en colonnes si beaucoup de valeurs
                if len(values) > 10:
                    cols = st.columns(3)
                    for i, val in enumerate(values):
                        cols[i % 3].write(f"- {val}")
                else:
                    st.write(", ".join(values))
                st.markdown("---")


# -----------------------------------------------------------------------------
# Tab: Flotteurs
# -----------------------------------------------------------------------------
with tab_flot:
    st.markdown(f"### {FLOTTEUR_SCHEMA.display_name}")
    st.info(f"Entite enfant - {len(FLOTTEUR_SCHEMA.fields)} champs | Relation 1:N avec Operation")

    # Tableau du dictionnaire
    df_flot = build_dictionary_dataframe(FLOTTEUR_SCHEMA)
    st.dataframe(df_flot, use_container_width=True, hide_index=True)

    # Expander pour les valeurs d'enumeration
    enum_fields_flot = get_enum_fields(FLOTTEUR_SCHEMA)
    if enum_fields_flot:
        with st.expander("📋 Valeurs des enumerations", expanded=False):
            for field in enum_fields_flot:
                values = getattr(enums, field.enum_ref, [])
                st.markdown(f"**{field.label}** (`{field.enum_ref}`)")
                st.write(", ".join(values))
                st.markdown("---")


# -----------------------------------------------------------------------------
# Tab: Resultats Humains
# -----------------------------------------------------------------------------
with tab_res:
    st.markdown(f"### {RESULTAT_HUMAIN_SCHEMA.display_name}")
    st.info(f"Entite enfant - {len(RESULTAT_HUMAIN_SCHEMA.fields)} champs | Relation 1:N avec Operation")

    # Tableau du dictionnaire
    df_res = build_dictionary_dataframe(RESULTAT_HUMAIN_SCHEMA)
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    # Expander pour les valeurs d'enumeration
    enum_fields_res = get_enum_fields(RESULTAT_HUMAIN_SCHEMA)
    if enum_fields_res:
        with st.expander("📋 Valeurs des enumerations", expanded=False):
            for field in enum_fields_res:
                values = getattr(enums, field.enum_ref, [])
                st.markdown(f"**{field.label}** (`{field.enum_ref}`)")
                st.write(", ".join(values))
                st.markdown("---")


# =============================================================================
# Section: Relations entre entites
# =============================================================================
st.divider()
st.subheader("🔗 Relations entre entites")

# Diagramme Mermaid simplifie
mermaid_relations = """
erDiagram
    operations ||--o{ flotteurs : "1:N"
    operations ||--o{ resultats_humain : "1:N"

    operations {
        int operation_id PK
        string cross
        string type_operation
        timestamp date_heure_reception_alerte
    }

    flotteurs {
        int flotteur_id PK
        int operation_id FK
        string type_flotteur
        string resultat_flotteur
    }

    resultats_humain {
        int resultat_id PK
        int operation_id FK
        string categorie_personne
        string resultat_humain
        int nombre
    }
"""

# Essayer d'afficher avec streamlit-mermaid, sinon fallback sur code
try:
    from streamlit_mermaid import st_mermaid
    st_mermaid(mermaid_relations, height=350)
except ImportError:
    st.code(mermaid_relations, language="mermaid")
    st.caption("Pour un rendu visuel, installer: `pip install streamlit-mermaid`")


# =============================================================================
# Section: Source des donnees
# =============================================================================
st.divider()
st.subheader("📖 Source des donnees")

st.markdown("""
Les descriptions des champs proviennent de la documentation officielle SECMAR :
- [Schema SECMAR](https://mtes-mct.github.io/secmar-documentation/schema.html)
- [Tables de codes](https://mtes-mct.github.io/secmar-documentation/tables_codes.html)

Les valeurs des enumerations incluent les valeurs historiques (avant 2020) pour
compatibilite avec les donnees legacy.
""")

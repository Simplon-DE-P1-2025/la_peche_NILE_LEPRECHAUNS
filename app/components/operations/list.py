"""Composant liste des operations avec filtres et pagination.

Version schema-driven: les colonnes sont definies dans le schema
et le DataFrame est genere automatiquement.
"""

import streamlit as st
from typing import Callable

from src.database.connection import get_session
from src.database.crud import crud_operation
from src.database.raw_queries import get_cross_list, get_type_list

from src.schema import ListGenerator
from src.schema.schemas import OPERATION_SCHEMA


# Instance du generateur de listes pour les operations
_list_gen = ListGenerator(OPERATION_SCHEMA)


def render_filters() -> dict:
    """Affiche les filtres et retourne les valeurs selectionnees.

    Returns:
        dict avec les cles: cross, type_operation, date_debut, date_fin
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cross_options = ["Tous"] + get_cross_list()
        filter_cross = st.selectbox("CROSS", options=cross_options, key="filter_cross")
        filter_cross = None if filter_cross == "Tous" else filter_cross

    with col2:
        type_options = ["Tous"] + get_type_list()
        filter_type = st.selectbox("Type", options=type_options, key="filter_type")
        filter_type = None if filter_type == "Tous" else filter_type

    with col3:
        filter_date_debut = st.date_input("Date debut", value=None, key="filter_date_debut")

    with col4:
        filter_date_fin = st.date_input("Date fin", value=None, key="filter_date_fin")

    return {
        "cross": filter_cross,
        "type_operation": filter_type,
        "date_debut": filter_date_debut,
        "date_fin": filter_date_fin,
    }


@st.fragment
def render_list(filters: dict, on_select: Callable[[int], None]) -> None:
    """Affiche la liste des operations avec pagination.

    Les colonnes sont generees automatiquement a partir du schema.

    Args:
        filters: Dictionnaire des filtres (cross, type_operation, date_debut, date_fin)
        on_select: Callback appele avec l'ID de l'operation selectionnee
    """
    # Pagination
    col1, col2 = st.columns([1, 3])
    with col1:
        per_page = st.selectbox("Par page", options=[10, 25, 50, 100], index=1, key="ops_per_page")
    with col2:
        page = st.number_input("Page", min_value=1, value=1, key="ops_page")

    # Charger les donnees
    with get_session() as session:
        operations = crud_operation.search(
            session,
            cross=filters.get("cross"),
            type_operation=filters.get("type_operation"),
            date_debut=filters.get("date_debut"),
            date_fin=filters.get("date_fin"),
            skip=(page - 1) * per_page,
            limit=per_page
        )

        total = crud_operation.count_filtered(
            session,
            cross=filters.get("cross"),
            type_operation=filters.get("type_operation"),
            date_debut=filters.get("date_debut"),
            date_fin=filters.get("date_fin")
        )

    total_pages = (total // per_page) + (1 if total % per_page else 0)
    st.caption(f"Total: {total} operations | Page {page}/{max(1, total_pages)}")

    if operations:
        # Construire le DataFrame via le generateur (schema-driven)
        df = _list_gen.build_dataframe(operations, include_id=True)

        # Afficher avec selection
        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config=_list_gen.get_column_config(),
        )

        # Gerer la selection
        if event.selection.rows:
            selected_idx = event.selection.rows[0]
            selected_id = int(df.iloc[selected_idx]["ID"])
            on_select(selected_id)
    else:
        st.info("Aucune operation trouvee avec ces filtres")

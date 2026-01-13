"""Composant liste des flotteurs d'une operation.

Version schema-driven: les colonnes sont definies dans le schema
et le DataFrame est genere automatiquement.
"""

import streamlit as st

from src.database.connection import get_session
from src.database.crud import crud_flotteur
from src.auth.authentificator import has_role
from app.components.state import start_edit_flotteur, start_create_flotteur

from src.schema import ListGenerator
from src.schema.schemas import FLOTTEUR_SCHEMA


# Instance du generateur de listes pour les flotteurs
_list_gen = ListGenerator(FLOTTEUR_SCHEMA)


@st.fragment
def render_flotteur_list(operation_id: int) -> None:
    """Affiche la liste des flotteurs d'une operation avec actions.

    Les colonnes sont generees automatiquement a partir du schema.

    Args:
        operation_id: ID de l'operation parente
    """
    # Bouton ajouter (si editeur)
    if has_role("editor"):
        if st.button("Ajouter un flotteur", key="btn_add_flotteur", type="secondary"):
            start_create_flotteur()
            st.rerun(scope="app")

    # Charger les flotteurs
    with get_session() as session:
        flotteurs = crud_flotteur.get_by_operation(session, int(operation_id))

    if not flotteurs:
        st.caption("Aucun flotteur enregistre pour cette operation")
        return

    # Construire le DataFrame via le generateur (schema-driven)
    df = _list_gen.build_dataframe(flotteurs, include_id=True)

    # Affichage avec selection
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=_list_gen.get_column_config(),
        key="flotteur_table"
    )

    # Gerer la selection pour edition
    if event.selection.rows and has_role("editor"):
        selected_idx = event.selection.rows[0]
        selected_id = int(df.iloc[selected_idx]["ID"])
        st.caption(f"Flotteur #{selected_id} selectionne")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Modifier", key="btn_edit_flotteur"):
                start_edit_flotteur(selected_id)
                st.rerun(scope="app")

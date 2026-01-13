"""Composant liste des resultats humains d'une operation.

Version schema-driven: les colonnes sont definies dans le schema
et le DataFrame est genere automatiquement (avec emoji via formatter).
"""

import streamlit as st

from src.database.connection import get_session
from src.database.crud import crud_resultat_humain
from src.auth.authentificator import has_role
from app.components.state import start_edit_resultat, start_create_resultat

from src.schema import ListGenerator
from src.schema.schemas import RESULTAT_HUMAIN_SCHEMA


# Instance du generateur de listes pour les resultats humains
_list_gen = ListGenerator(RESULTAT_HUMAIN_SCHEMA)


@st.fragment
def render_resultat_list(operation_id: int) -> None:
    """Affiche la liste des resultats humains d'une operation avec actions.

    Les colonnes sont generees automatiquement a partir du schema.
    Le formatter emoji est applique automatiquement au champ resultat_humain.

    Args:
        operation_id: ID de l'operation parente
    """
    # Bouton ajouter (si editeur)
    if has_role("editor"):
        if st.button("Ajouter un resultat", key="btn_add_resultat", type="secondary"):
            start_create_resultat()
            st.rerun(scope="app")

    # Charger les resultats
    with get_session() as session:
        resultats = crud_resultat_humain.get_by_operation(session, int(operation_id))

    if not resultats:
        st.caption("Aucun resultat humain enregistre pour cette operation")
        return

    # Construire le DataFrame via le generateur (schema-driven avec emoji formatter)
    df = _list_gen.build_dataframe(resultats, include_id=True)

    # Affichage avec selection
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config=_list_gen.get_column_config(),
        key="resultat_table"
    )

    # Gerer la selection pour edition
    if event.selection.rows and has_role("editor"):
        selected_idx = event.selection.rows[0]
        selected_id = int(df.iloc[selected_idx]["ID"])
        st.caption(f"Resultat #{selected_id} selectionne")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Modifier", key="btn_edit_resultat"):
                start_edit_resultat(selected_id)
                st.rerun(scope="app")


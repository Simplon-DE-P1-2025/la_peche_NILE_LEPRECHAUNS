"""Formulaires pour creation/edition de flotteurs.

Version schema-driven: les formulaires sont generes automatiquement
a partir du schema defini dans src/schema/schemas/flotteur.py.
"""

import streamlit as st

from src.auth.authentificator import get_current_user, has_role
from app.components.state import cancel_flotteur_form

from src.schema import DialogGenerator
from src.schema.schemas import FLOTTEUR_SCHEMA


# Instance du generateur de dialogs pour les flotteurs
_dialog_gen = DialogGenerator(FLOTTEUR_SCHEMA)


@st.dialog("Ajouter un flotteur")
def dialog_create_flotteur(operation_id: int) -> None:
    """Dialog modal pour creer un nouveau flotteur.

    Genere automatiquement a partir du schema FLOTTEUR_SCHEMA.

    Args:
        operation_id: ID de l'operation parente
    """
    user = get_current_user()
    username = user["username"] if user else "anonymous"

    st.caption(f"Operation #{operation_id}")

    def on_success():
        cancel_flotteur_form()
        st.rerun(scope="app")

    def on_cancel():
        cancel_flotteur_form()
        st.rerun(scope="app")

    _dialog_gen.create_dialog(
        user=username,
        parent_id=int(operation_id),
        exclude_fields={"flotteur_id", "operation_id"},
        on_success=on_success,
        on_cancel=on_cancel,
    )


@st.dialog("Modifier le flotteur")
def dialog_edit_flotteur(flotteur_id: int) -> None:
    """Dialog modal pour modifier un flotteur existant.

    Genere automatiquement a partir du schema FLOTTEUR_SCHEMA.

    Args:
        flotteur_id: ID du flotteur a modifier
    """
    user = get_current_user()
    username = user["username"] if user else "anonymous"

    def on_success():
        cancel_flotteur_form()
        st.rerun(scope="app")

    def on_cancel():
        cancel_flotteur_form()
        st.rerun(scope="app")

    def on_delete():
        cancel_flotteur_form()
        st.rerun(scope="app")

    _dialog_gen.edit_dialog(
        entity_id=flotteur_id,
        user=username,
        can_delete=has_role("admin"),
        exclude_fields={"operation_id"},
        on_success=on_success,
        on_delete=on_delete,
        on_cancel=on_cancel,
    )

"""Formulaires pour creation/edition de resultats humains.

Version schema-driven: les formulaires sont generes automatiquement
a partir du schema defini dans src/schema/schemas/resultat_humain.py.
"""

import streamlit as st

from src.auth.authentificator import get_current_user, has_role
from app.components.state import cancel_resultat_form

from src.schema import DialogGenerator
from src.schema.schemas import RESULTAT_HUMAIN_SCHEMA


# Instance du generateur de dialogs pour les resultats humains
_dialog_gen = DialogGenerator(RESULTAT_HUMAIN_SCHEMA)


@st.dialog("Ajouter un resultat humain")
def dialog_create_resultat(operation_id: int) -> None:
    """Dialog modal pour creer un nouveau resultat humain.

    Genere automatiquement a partir du schema RESULTAT_HUMAIN_SCHEMA.

    Args:
        operation_id: ID de l'operation parente
    """
    user = get_current_user()
    username = user["username"] if user else "anonymous"

    st.caption(f"Operation #{operation_id}")

    def on_success():
        cancel_resultat_form()
        st.rerun(scope="app")

    def on_cancel():
        cancel_resultat_form()
        st.rerun(scope="app")

    _dialog_gen.create_dialog(
        user=username,
        parent_id=int(operation_id),
        exclude_fields={"resultat_id", "operation_id"},
        on_success=on_success,
        on_cancel=on_cancel,
    )


@st.dialog("Modifier le resultat")
def dialog_edit_resultat(resultat_id: int) -> None:
    """Dialog modal pour modifier un resultat humain existant.

    Genere automatiquement a partir du schema RESULTAT_HUMAIN_SCHEMA.

    Args:
        resultat_id: ID du resultat a modifier
    """
    user = get_current_user()
    username = user["username"] if user else "anonymous"

    def on_success():
        cancel_resultat_form()
        st.rerun(scope="app")

    def on_cancel():
        cancel_resultat_form()
        st.rerun(scope="app")

    def on_delete():
        cancel_resultat_form()
        st.rerun(scope="app")

    _dialog_gen.edit_dialog(
        entity_id=resultat_id,
        user=username,
        can_delete=has_role("admin"),
        exclude_fields={"operation_id"},
        on_success=on_success,
        on_delete=on_delete,
        on_cancel=on_cancel,
    )

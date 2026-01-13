"""Formulaires pour creation/edition d'operations.

Version schema-driven: les formulaires sont generes automatiquement
a partir du schema defini dans src/schema/schemas/operation.py.

Pour ajouter un nouveau champ:
1. Ajouter le FieldSchema dans operation.py
2. Les formulaires se mettent a jour automatiquement!
"""

import streamlit as st
from typing import Any
from sqlalchemy import func

from src.database.connection import get_session
from src.database.crud import crud_operation
from src.database.models import Operation
from src.auth.authentificator import get_current_user, has_role
from app.components.state import cancel_edit_operation

from src.schema import DialogGenerator
from src.schema.schemas import OPERATION_SCHEMA


# Instance du generateur de dialogs pour les operations
_dialog_gen = DialogGenerator(OPERATION_SCHEMA)


def _get_next_operation_id() -> int:
    """Calcule le prochain operation_id disponible (max + 1)."""
    with get_session() as session:
        max_id = session.query(func.max(Operation.operation_id)).scalar()
        return (max_id or 0) + 1


@st.dialog("Nouvelle operation")
def dialog_create_operation() -> None:
    """Dialog modal pour creer une nouvelle operation.

    Genere automatiquement a partir du schema OPERATION_SCHEMA.
    """
    user = get_current_user()
    username = user["username"] if user else "anonymous"

    # Calculer le prochain ID disponible
    next_id = _get_next_operation_id()

    def on_success():
        st.rerun(scope="app")

    _dialog_gen.create_dialog(
        user=username,
        initial_values={"operation_id": next_id},
        on_success=on_success,
    )


@st.dialog("Modifier l'operation")
def dialog_edit_operation(operation_id: int) -> None:
    """Dialog modal pour modifier une operation existante.

    Genere automatiquement a partir du schema OPERATION_SCHEMA.

    Args:
        operation_id: ID de l'operation a modifier
    """
    user = get_current_user()
    username = user["username"] if user else "anonymous"

    def on_success():
        cancel_edit_operation()
        st.rerun(scope="app")

    def on_cancel():
        cancel_edit_operation()
        st.rerun(scope="app")

    def on_delete():
        cancel_edit_operation()
        st.session_state["ops_view"] = "list"
        st.session_state["ops_selected_id"] = None
        st.rerun(scope="app")

    _dialog_gen.edit_dialog(
        entity_id=operation_id,
        user=username,
        can_delete=has_role("admin"),
        on_success=on_success,
        on_delete=on_delete,
        on_cancel=on_cancel,
    )


def render_form(operation: Any = None) -> None:
    """Affiche le formulaire dans la page (alternative aux dialogs).

    Args:
        operation: Si fourni, mode edition. Sinon, mode creation.
    """
    if operation:
        dialog_edit_operation(operation.operation_id)
    else:
        dialog_create_operation()

"""Composants reutilisables pour l'application Streamlit SECMAR."""

from .state import (
    init_state,
    set_view,
    select_operation,
    start_edit_operation,
    cancel_edit_operation,
    start_create_flotteur,
    start_edit_flotteur,
    cancel_flotteur_form,
    start_create_resultat,
    start_edit_resultat,
    cancel_resultat_form,
)

__all__ = [
    "init_state",
    "set_view",
    "select_operation",
    "start_edit_operation",
    "cancel_edit_operation",
    "start_create_flotteur",
    "start_edit_flotteur",
    "cancel_flotteur_form",
    "start_create_resultat",
    "start_edit_resultat",
    "cancel_resultat_form",
]

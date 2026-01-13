"""Composants pour la gestion des flotteurs."""

from .list import render_flotteur_list
from .form import dialog_create_flotteur, dialog_edit_flotteur

__all__ = [
    "render_flotteur_list",
    "dialog_create_flotteur",
    "dialog_edit_flotteur",
]

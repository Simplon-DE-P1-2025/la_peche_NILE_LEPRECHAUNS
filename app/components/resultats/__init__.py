"""Composants pour la gestion des resultats humains."""

from .list import render_resultat_list
from .form import dialog_create_resultat, dialog_edit_resultat

__all__ = [
    "render_resultat_list",
    "dialog_create_resultat",
    "dialog_edit_resultat",
]

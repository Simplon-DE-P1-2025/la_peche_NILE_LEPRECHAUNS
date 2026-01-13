"""Composants pour la gestion des operations."""

from .list import render_filters, render_list
from .detail import render_header, render_stats
from .form import render_form, dialog_create_operation, dialog_edit_operation

__all__ = [
    "render_filters",
    "render_list",
    "render_header",
    "render_stats",
    "render_form",
    "dialog_create_operation",
    "dialog_edit_operation",
]

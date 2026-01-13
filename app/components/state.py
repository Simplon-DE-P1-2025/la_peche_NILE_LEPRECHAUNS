"""Gestion centralisee du session_state pour la page Operations."""

import streamlit as st


def init_state() -> None:
    """Initialise les cles de session si absentes."""
    defaults = {
        "ops_view": "list",
        "ops_selected_id": None,
        "ops_edit_mode": False,  # Pour editer l'operation
        "flotteur_mode": None,
        "flotteur_edit_id": None,
        "resultat_mode": None,
        "resultat_edit_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_view(mode: str) -> None:
    """Change le mode de vue (list, detail, create)."""
    st.session_state["ops_view"] = mode
    # Reset les modes edition quand on change de vue
    if mode != "detail":
        st.session_state["ops_edit_mode"] = False
        st.session_state["flotteur_mode"] = None
        st.session_state["flotteur_edit_id"] = None
        st.session_state["resultat_mode"] = None
        st.session_state["resultat_edit_id"] = None


def select_operation(operation_id: int) -> None:
    """Selectionne une operation et passe en mode detail."""
    st.session_state["ops_selected_id"] = operation_id
    st.session_state["ops_view"] = "detail"
    # Reset les modes edition
    st.session_state["ops_edit_mode"] = False
    st.session_state["flotteur_mode"] = None
    st.session_state["flotteur_edit_id"] = None
    st.session_state["resultat_mode"] = None
    st.session_state["resultat_edit_id"] = None


def start_edit_operation() -> None:
    """Demarre l'edition de l'operation."""
    st.session_state["ops_edit_mode"] = True
    # Reset les autres modes
    st.session_state["flotteur_mode"] = None
    st.session_state["resultat_mode"] = None


def cancel_edit_operation() -> None:
    """Annule l'edition de l'operation."""
    st.session_state["ops_edit_mode"] = False


def start_create_flotteur() -> None:
    """Demarre la creation d'un flotteur."""
    st.session_state["ops_edit_mode"] = False
    st.session_state["resultat_mode"] = None
    st.session_state["flotteur_mode"] = "create"
    st.session_state["flotteur_edit_id"] = None


def start_edit_flotteur(flotteur_id: int) -> None:
    """Demarre l'edition d'un flotteur."""
    st.session_state["ops_edit_mode"] = False
    st.session_state["resultat_mode"] = None
    st.session_state["flotteur_mode"] = "edit"
    st.session_state["flotteur_edit_id"] = flotteur_id


def cancel_flotteur_form() -> None:
    """Annule le formulaire flotteur."""
    st.session_state["flotteur_mode"] = None
    st.session_state["flotteur_edit_id"] = None


def start_create_resultat() -> None:
    """Demarre la creation d'un resultat."""
    st.session_state["ops_edit_mode"] = False
    st.session_state["flotteur_mode"] = None
    st.session_state["resultat_mode"] = "create"
    st.session_state["resultat_edit_id"] = None


def start_edit_resultat(resultat_id: int) -> None:
    """Demarre l'edition d'un resultat."""
    st.session_state["ops_edit_mode"] = False
    st.session_state["flotteur_mode"] = None
    st.session_state["resultat_mode"] = "edit"
    st.session_state["resultat_edit_id"] = resultat_id


def cancel_resultat_form() -> None:
    """Annule le formulaire resultat."""
    st.session_state["resultat_mode"] = None
    st.session_state["resultat_edit_id"] = None

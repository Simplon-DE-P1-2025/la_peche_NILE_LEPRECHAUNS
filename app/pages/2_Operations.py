"""Page unifiee de gestion des operations SECMAR.

Cette page permet de:
- Consulter la liste des operations avec filtres avances
- Voir le detail d'une operation avec ses flotteurs et resultats humains
- Creer de nouvelles operations
- Modifier/supprimer des operations existantes (selon roles)
- Gerer les flotteurs et resultats directement depuis le detail

Auteur: Equipe Sprint 3-4
Date: Janvier 2026
"""
import streamlit as st
import sys
from pathlib import Path

# Configuration du path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info, has_role
from src.database.connection import get_session
from src.database.crud import crud_operation

from app.components.state import init_state, set_view, select_operation, start_edit_operation
from app.components.operations.list import render_filters, render_list
from app.components.operations.detail import render_header
from app.components.operations.form import dialog_create_operation, dialog_edit_operation
from app.components.flotteurs.list import render_flotteur_list
from app.components.flotteurs.form import dialog_create_flotteur, dialog_edit_flotteur
from app.components.resultats.list import render_resultat_list
from app.components.resultats.form import dialog_create_resultat, dialog_edit_resultat


# =============================================================================
# Configuration de la page Streamlit
# =============================================================================
st.set_page_config(
    page_title="Operations SECMAR",
    page_icon=":mag:",
    layout="wide"
)


# =============================================================================
# Authentification
# =============================================================================
if not login_required():
    st.stop()

show_user_info()


# =============================================================================
# Initialisation de l'etat
# =============================================================================
init_state()


# =============================================================================
# En-tete de la page
# =============================================================================
st.title(":mag: Gestion des Operations")

# Barre de navigation
col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    if st.button(":clipboard: Liste", type="secondary" if st.session_state.get("ops_view") != "list" else "primary"):
        set_view("list")
        st.rerun()

with col2:
    if has_role("editor"):
        if st.button(":heavy_plus_sign: Nouvelle operation"):
            dialog_create_operation()

st.markdown("---")


# =============================================================================
# Contenu selon le mode
# =============================================================================
mode = st.session_state.get("ops_view", "list")


# -----------------------------------------------------------------------------
# MODE LISTE
# -----------------------------------------------------------------------------
if mode == "list":
    st.subheader("Liste des operations")

    # Filtres
    filters = render_filters()

    # Liste avec callback de selection
    def on_operation_selected(op_id: int):
        select_operation(op_id)
        st.rerun()

    render_list(filters, on_operation_selected)


# -----------------------------------------------------------------------------
# MODE DETAIL
# -----------------------------------------------------------------------------
elif mode == "detail":
    operation_id = st.session_state.get("ops_selected_id")

    if not operation_id:
        st.warning("Aucune operation selectionnee")
        set_view("list")
        st.rerun()

    # Bouton retour
    if st.button(":arrow_left: Retour a la liste"):
        set_view("list")
        st.rerun()

    # Charger l'operation avec ses relations
    with get_session() as session:
        operation = crud_operation.get_with_relations(session, operation_id)

    if not operation:
        st.error(f"Operation {operation_id} non trouvee")
        set_view("list")
        st.rerun()

    # Gestion des dialogs (un seul a la fois autorise par Streamlit)
    ops_edit_mode = st.session_state.get("ops_edit_mode")
    flotteur_mode = st.session_state.get("flotteur_mode")
    resultat_mode = st.session_state.get("resultat_mode")

    if ops_edit_mode:
        dialog_edit_operation(operation_id)
    elif flotteur_mode == "create":
        dialog_create_flotteur(operation_id)
    elif flotteur_mode == "edit":
        flotteur_id = st.session_state.get("flotteur_edit_id")
        if flotteur_id:
            dialog_edit_flotteur(flotteur_id)
    elif resultat_mode == "create":
        dialog_create_resultat(operation_id)
    elif resultat_mode == "edit":
        resultat_id = st.session_state.get("resultat_edit_id")
        if resultat_id:
            dialog_edit_resultat(resultat_id)

    # En-tete avec titre et bouton modifier
    col_title, col_edit = st.columns([4, 1])
    with col_title:
        st.subheader(f"Operation #{operation_id}")
    with col_edit:
        if has_role("editor"):
            if st.button(":pencil2: Modifier", key="btn_edit_operation"):
                start_edit_operation()
                st.rerun()

    # Informations generales
    st.markdown("#### Informations generales")
    render_header(operation)

    # Section Flotteurs
    st.markdown("---")
    st.markdown("#### :ship: Flotteurs")
    render_flotteur_list(operation_id)

    # Section Resultats humains
    st.markdown("---")
    st.markdown("#### :busts_in_silhouette: Resultats humains")
    render_resultat_list(operation_id)

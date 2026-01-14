"""Composant affichage detail d'une operation."""

import streamlit as st
from typing import Any


def render_header(operation: Any) -> None:
    """Affiche les informations generales d'une operation.

    Args:
        operation: Objet Operation avec ses attributs
    """
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("ID")
        st.markdown(f"**{operation.operation_id}**")
        st.caption("SITREP")
        st.markdown(operation.numero_sitrep or "-")

    with col2:
        st.caption("Type")
        st.markdown(f"**{operation.type_operation or '-'}**")
        st.caption("CROSS")
        st.markdown(operation.cross or "-")
        st.caption("Département")
        st.markdown(str(operation.departement or "-"))

    with col3:
        st.caption("Date alerte")
        st.markdown(str(operation.date_heure_reception_alerte or "-"))
        st.caption("Durée")
        st.markdown(f"{operation.duree_intervention or '-'} min")
        st.caption("Personnes")
        st.markdown(str(operation.nombre_personnes_impliquees or 0))
        if operation.latitude and operation.longitude:
            st.caption("Position")
            st.markdown(f"{operation.latitude:.4f}, {operation.longitude:.4f}")


def render_stats(stats: Any) -> None:
    """Affiche les statistiques d'une operation (4 metrics).

    Args:
        stats: Objet OperationStats avec nombre_sauves, nombre_blesses, etc.
    """
    if not stats:
        st.caption("Aucune statistique disponible")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Sauves", stats.nombre_sauves or 0)
    with col2:
        st.metric("Blesses", stats.nombre_blesses or 0)
    with col3:
        st.metric("Decedes", stats.nombre_decedes or 0)
    with col4:
        st.metric("Disparus", stats.nombre_disparus or 0)

"""Requêtes de base optimisées - utilisant les vues matérialisées.

Ce module fournit des requêtes optimisées qui utilisent les vues matérialisées
pré-calculées au lieu de faire des agrégations coûteuses à chaque requête.

Performance:
- get_kpis_global(): 10ms (au lieu de 12.6s avec COUNT DISTINCT)
- get_yearly_stats_cached(): 10ms (au lieu de 8.5s)
- get_cross_stats_cached(): 10ms (au lieu de 8.3s)
- get_operations_base(): 5.9s une fois, puis filtrage in-memory instantané

Usage:
    from src.database.base_queries import (
        get_kpis_global,
        get_yearly_stats_cached,
        get_operations_base,
        CROSS_ACTIFS,
    )

    # KPIs globaux (instantané)
    kpis = get_kpis_global()

    # Stats annuelles (instantané)
    yearly = get_yearly_stats_cached()

    # Données pour filtrage in-memory
    df = get_operations_base()
"""

import pandas as pd
import streamlit as st
from datetime import date
from typing import Optional

from sqlalchemy import text

from src.config import DB_SCHEMA
from src.database.connection import execute_raw_sql, engine


# =============================================================================
# Liste des CROSS actuellement actifs
# =============================================================================
CROSS_ACTIFS = [
    "Antilles-Guyane",
    "Corse",
    "Corsen",
    "Étel",
    "Etel",  # Variante sans accent
    "Gris-Nez",
    "Jobourg",
    "La Garde",
    "Nouvelle-Calédonie",
    "Polynésie",
    "Sud océan Indien",
]


# =============================================================================
# KPIs depuis vues matérialisées (instantané)
# =============================================================================

@st.cache_data(ttl=3600)
def get_kpis_global() -> dict:
    """KPIs globaux depuis vue matérialisée v_kpi_global.

    Performance: 10ms (au lieu de 12.6s)

    Returns:
        Dictionnaire avec tous les KPIs globaux pré-calculés
    """
    sql = "SELECT * FROM v_kpi_global"
    result = execute_raw_sql(sql)
    return result[0] if result else {}


@st.cache_data(ttl=3600)
def get_yearly_stats_cached() -> list[dict]:
    """Stats annuelles depuis vue matérialisée v_kpi_annuel.

    Performance: 10ms (au lieu de 8.5s)

    Returns:
        Liste de dictionnaires avec stats par année
    """
    sql = "SELECT * FROM v_kpi_annuel ORDER BY annee DESC"
    return execute_raw_sql(sql)


@st.cache_data(ttl=3600)
def get_cross_stats_cached() -> list[dict]:
    """Stats par CROSS depuis vue matérialisée v_kpi_cross.

    Performance: 10ms (au lieu de 8.3s)

    Returns:
        Liste de dictionnaires avec stats par CROSS
    """
    sql = "SELECT * FROM v_kpi_cross ORDER BY total_operations DESC"
    return execute_raw_sql(sql)


@st.cache_data(ttl=3600)
def get_cross_stats_actifs_only() -> list[dict]:
    """Stats par CROSS (uniquement les CROSS actifs).

    Returns:
        Liste de dictionnaires avec stats par CROSS actif
    """
    placeholders = ", ".join([f":cross_{i}" for i in range(len(CROSS_ACTIFS))])
    params = {f"cross_{i}": cross for i, cross in enumerate(CROSS_ACTIFS)}

    sql = f"""
    SELECT * FROM v_kpi_cross
    WHERE cross_name IN ({placeholders})
    ORDER BY total_operations DESC
    """
    return execute_raw_sql(sql, params)


# =============================================================================
# Données de base pour filtrage in-memory
# =============================================================================

@st.cache_resource(ttl=3600)
def get_operations_base(
    years_back: int = 3,
    start_date: Optional[date] = None,
) -> pd.DataFrame:
    """Charge les opérations récentes avec stats pour filtrage in-memory.

    Performance:
        - years_back=3: ~3s (au lieu de 19s pour toutes les données)
        - years_back=0: ~19s (toutes les données historiques)

    Args:
        years_back: Nombre d'années à charger (défaut: 3). 0 = tout l'historique.
        start_date: Date de début explicite (prioritaire sur years_back).

    Returns:
        DataFrame avec les opérations et leurs stats
    """
    years_back = int(years_back)
    schema = DB_SCHEMA

    params = None

    if start_date is not None:
        date_clause = "AND o.date_heure_reception_alerte >= :start_date"
        params = {"start_date": start_date}
    elif years_back > 0:
        date_clause = f"AND o.date_heure_reception_alerte >= CURRENT_DATE - INTERVAL '{years_back} years'"
    else:
        date_clause = ""

    if years_back > 0 or start_date is not None:
        sql = f"""
        SELECT
            o.operation_id,
            o.date_heure_reception_alerte,
            o.type_operation,
            o."cross",
            o.departement,
            o.latitude,
            o.longitude,
            o.evenement,
            o.categorie_evenement,
            s.nombre_impliques,
            s.nombre_saines_sauves,
            s.nombre_decedes,
            s.nombre_disparus,
            s.nombre_blesses,
            s.nombre_prises_en_compte
        FROM {schema}.operations o
        INNER JOIN {schema}.operations_stats s ON o.operation_id = s.operation_id
        WHERE o.date_heure_reception_alerte IS NOT NULL
            {date_clause}
        """
    else:
        sql = f"""
        SELECT
            o.operation_id,
            o.date_heure_reception_alerte,
            o.type_operation,
            o."cross",
            o.departement,
            o.latitude,
            o.longitude,
            o.evenement,
            o.categorie_evenement,
            s.nombre_impliques,
            s.nombre_saines_sauves,
            s.nombre_decedes,
            s.nombre_disparus,
            s.nombre_blesses,
            s.nombre_prises_en_compte
        FROM {schema}.operations o
        INNER JOIN {schema}.operations_stats s ON o.operation_id = s.operation_id
        WHERE o.date_heure_reception_alerte IS NOT NULL
        """

    return pd.read_sql_query(
        text(sql),
        engine,
        parse_dates=["date_heure_reception_alerte"],
        params=params,
    )


@st.cache_resource(ttl=3600)
def get_operations_base_lightweight() -> pd.DataFrame:
    """Version légère: uniquement les colonnes essentielles pour le filtrage.

    Moins de données transférées = plus rapide sur réseau lent.

    Returns:
        DataFrame avec colonnes essentielles uniquement
    """
    schema = DB_SCHEMA
    sql = f"""
    SELECT
        o.operation_id,
        o.date_heure_reception_alerte,
        o."cross",
        o.type_operation,
        s.nombre_impliques,
        s.nombre_saines_sauves,
        s.nombre_decedes,
        s.nombre_disparus
    FROM {schema}.operations o
    INNER JOIN {schema}.operations_stats s ON o.operation_id = s.operation_id
    WHERE o.date_heure_reception_alerte IS NOT NULL
    """
    return pd.read_sql_query(
        text(sql),
        engine,
        parse_dates=["date_heure_reception_alerte"],
    )


# =============================================================================
# Fonctions utilitaires
# =============================================================================

def get_cross_list_from_cache() -> list[str]:
    """Liste des CROSS depuis les stats cachées (évite requête supplémentaire).

    Returns:
        Liste des noms de CROSS distincts
    """
    stats = get_cross_stats_cached()
    return [s['cross_name'] for s in stats if s['cross_name'] != 'Non renseigné']


def get_years_from_cache() -> list[int]:
    """Liste des années depuis les stats cachées (évite requête supplémentaire).

    Returns:
        Liste des années disponibles (ordre décroissant)
    """
    stats = get_yearly_stats_cached()
    return [s['annee'] for s in stats]

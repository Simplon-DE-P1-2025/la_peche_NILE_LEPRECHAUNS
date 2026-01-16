"""Module de warmload pour pré-charger les caches critiques au démarrage.

Ce module permet de pré-charger les données les plus utilisées au démarrage
de l'application Streamlit, réduisant ainsi le temps de chargement initial
des pages.

Usage:
    from src.utils.warmload import warmload_critical_caches
    warmload_critical_caches()
"""

import streamlit as st
from typing import Optional
import time


def warmload_critical_caches(verbose: bool = False) -> dict:
    """Pré-charge tous les caches critiques au démarrage de l'application.

    Charge les données des vues matérialisées les plus utilisées pour
    initialiser le cache Streamlit. Cela permet aux pages de charger
    instantanément après le premier accès.

    Args:
        verbose: Si True, affiche les temps de chargement pour chaque cache

    Returns:
        Dictionnaire avec les temps de chargement de chaque cache
    """
    timings = {}

    # Éviter de recharger si déjà fait dans cette session
    if st.session_state.get("_warmload_done", False):
        return {"status": "already_loaded"}

    try:
        # Import des fonctions de requête
        from src.database.base_queries import (
            get_kpis_global,
            get_yearly_stats_cached,
            get_cross_stats_cached,
        )

        # 1. KPIs globaux (utilisé par main.py)
        start = time.time()
        get_kpis_global()
        timings["kpis_global"] = round((time.time() - start) * 1000, 2)
        if verbose:
            print(f"  ✓ kpis_global: {timings['kpis_global']}ms")

        # 2. Stats annuelles (utilisé par Dashboard)
        start = time.time()
        get_yearly_stats_cached()
        timings["yearly_stats"] = round((time.time() - start) * 1000, 2)
        if verbose:
            print(f"  ✓ yearly_stats: {timings['yearly_stats']}ms")

        # 3. Stats par CROSS (utilisé par Dashboard et filtres)
        start = time.time()
        get_cross_stats_cached()
        timings["cross_stats"] = round((time.time() - start) * 1000, 2)
        if verbose:
            print(f"  ✓ cross_stats: {timings['cross_stats']}ms")

        # Marquer le warmload comme effectué
        st.session_state["_warmload_done"] = True
        timings["status"] = "success"
        timings["total"] = sum(v for k, v in timings.items() if isinstance(v, (int, float)))

        if verbose:
            print(f"  Total warmload: {timings['total']}ms")

    except Exception as e:
        timings["status"] = "error"
        timings["error"] = str(e)
        if verbose:
            print(f"  ✗ Erreur warmload: {e}")

    return timings


def warmload_extended_caches(verbose: bool = False) -> dict:
    """Pré-charge les caches étendus (optionnel, plus long).

    Inclut les données moins fréquemment utilisées mais qui peuvent
    bénéficier d'un pré-chargement pour améliorer l'expérience utilisateur.

    Args:
        verbose: Si True, affiche les temps de chargement

    Returns:
        Dictionnaire avec les temps de chargement
    """
    timings = warmload_critical_caches(verbose)

    if timings.get("status") == "error":
        return timings

    try:
        from src.database.kpi_queries import (
            get_kpi_cross_benchmark,
            get_kpi_yoy_comparison,
        )

        # 4. Benchmark CROSS (utilisé par Performance_CROSS.py)
        start = time.time()
        get_kpi_cross_benchmark()
        timings["cross_benchmark"] = round((time.time() - start) * 1000, 2)
        if verbose:
            print(f"  ✓ cross_benchmark: {timings['cross_benchmark']}ms")

        # 5. Comparaison YoY (utilisé par KPI_Securite.py)
        start = time.time()
        get_kpi_yoy_comparison()
        timings["yoy_comparison"] = round((time.time() - start) * 1000, 2)
        if verbose:
            print(f"  ✓ yoy_comparison: {timings['yoy_comparison']}ms")

        timings["total"] = sum(v for k, v in timings.items() if isinstance(v, (int, float)))

    except Exception as e:
        timings["extended_error"] = str(e)
        if verbose:
            print(f"  ✗ Erreur caches étendus: {e}")

    return timings


def reset_warmload_state() -> None:
    """Réinitialise l'état du warmload (utile pour les tests)."""
    if "_warmload_done" in st.session_state:
        del st.session_state["_warmload_done"]

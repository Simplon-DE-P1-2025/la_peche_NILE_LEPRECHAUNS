"""Outils de diagnostic et mesure de performance pour la base de données.

Ce module fournit des utilitaires pour:
- Mesurer la latence réseau vers la base de données
- Benchmarker les requêtes du Dashboard
- Comparer les temps avec/sans cache Streamlit

Usage:
    from src.utils.performance import measure_db_latency, benchmark_dashboard_queries

    # Mesurer la latence DB
    latency = measure_db_latency(iterations=10)
    print(f"Latence moyenne: {latency['avg_ms']:.2f}ms")

    # Benchmarker les requêtes du Dashboard
    results = benchmark_dashboard_queries()
    for r in results.queries:
        print(f"{r['name']}: {r['first_ms']:.2f}ms (sans cache)")
"""

import time
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import wraps
from typing import Callable, Any

from sqlalchemy import text

from src.database.connection import engine, get_session


@dataclass
class QueryResult:
    """Résultat d'un benchmark de requête."""
    name: str
    first_ms: float  # Temps sans cache (ou cache invalidé)
    cached_ms: float  # Temps avec cache
    rows_returned: int = 0
    error: str | None = None


@dataclass
class PerformanceResults:
    """Résultats complets du benchmark."""
    db_latency_avg_ms: float = 0.0
    db_latency_min_ms: float = 0.0
    db_latency_max_ms: float = 0.0
    db_latency_std_ms: float = 0.0
    queries: list[QueryResult] = field(default_factory=list)
    total_first_ms: float = 0.0
    total_cached_ms: float = 0.0

    @property
    def latency_status(self) -> str:
        """Retourne le status de la latence."""
        if self.db_latency_avg_ms < 20:
            return "excellent"
        elif self.db_latency_avg_ms < 50:
            return "bon"
        elif self.db_latency_avg_ms < 100:
            return "acceptable"
        elif self.db_latency_avg_ms < 200:
            return "lent"
        else:
            return "tres_lent"

    @property
    def recommendations(self) -> list[str]:
        """Génère des recommandations basées sur les résultats."""
        recs = []

        # Latence réseau
        if self.db_latency_avg_ms > 100:
            recs.append(
                f"Latence élevée ({self.db_latency_avg_ms:.0f}ms). "
                "Considérez une région DB plus proche ou un cache Redis."
            )
        elif self.db_latency_avg_ms > 50:
            recs.append(
                f"Latence modérée ({self.db_latency_avg_ms:.0f}ms). "
                "Le cache Streamlit devrait compenser après le premier chargement."
            )

        # Nombre de requêtes
        num_queries = len(self.queries)
        if num_queries > 10:
            recs.append(
                f"Trop de requêtes ({num_queries}). "
                "Combinez-les en 1-2 requêtes CTE pour réduire les round-trips."
            )

        # Temps total
        if self.total_first_ms > 2000:
            recs.append(
                f"Temps total élevé ({self.total_first_ms:.0f}ms sans cache). "
                "Impact: latence réseau × nombre de requêtes."
            )

        # Cache efficace
        if self.total_cached_ms < 100 and self.total_first_ms > 1000:
            recs.append(
                "Le cache Streamlit est efficace. "
                "Considérez un warmup au démarrage pour éviter le premier chargement lent."
            )

        if not recs:
            recs.append("Performances correctes. Aucune action urgente requise.")

        return recs


def measure_db_latency(iterations: int = 10) -> dict[str, float]:
    """Mesure la latence réseau vers la base de données.

    Effectue plusieurs requêtes SELECT 1 et calcule les statistiques.

    Args:
        iterations: Nombre de mesures à effectuer

    Returns:
        Dictionnaire avec avg_ms, min_ms, max_ms, std_ms
    """
    latencies = []

    for _ in range(iterations):
        start = time.perf_counter()
        with get_session() as session:
            session.execute(text("SELECT 1"))
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # Convertir en ms

    return {
        "avg_ms": statistics.mean(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "std_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "all_ms": latencies,
    }


def measure_query_time(func: Callable) -> Callable:
    """Décorateur pour mesurer le temps d'exécution d'une fonction.

    Usage:
        @measure_query_time
        def my_query():
            return execute_raw_sql("SELECT * FROM operations")

        result, timing = my_query()
        print(f"Temps: {timing['elapsed_ms']:.2f}ms")
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> tuple[Any, dict]:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()

        timing = {
            "elapsed_ms": (end - start) * 1000,
            "function": func.__name__,
        }
        return result, timing

    return wrapper


def _time_function(func: Callable, *args, **kwargs) -> tuple[float, Any, int]:
    """Mesure le temps d'exécution d'une fonction.

    Returns:
        Tuple (temps_ms, résultat, nombre_lignes)
    """
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        end = time.perf_counter()

        # Compter les lignes selon le type de résultat
        if isinstance(result, list):
            rows = len(result)
        elif isinstance(result, dict):
            rows = 1
        elif hasattr(result, '__len__'):
            rows = len(result)
        else:
            rows = 1 if result else 0

        return (end - start) * 1000, result, rows
    except Exception as e:
        end = time.perf_counter()
        return (end - start) * 1000, None, 0


def benchmark_dashboard_queries(
    date_debut: date | None = None,
    date_fin: date | None = None,
    clear_cache: bool = True,
) -> PerformanceResults:
    """Benchmark toutes les requêtes utilisées par le Dashboard.

    Args:
        date_debut: Date de début pour les requêtes filtrées (défaut: -365 jours)
        date_fin: Date de fin (défaut: aujourd'hui)
        clear_cache: Si True, invalide le cache avant le premier test

    Returns:
        PerformanceResults avec tous les résultats du benchmark
    """
    import streamlit as st
    import pandas as pd

    # ==========================================================================
    # Imports des fonctions OPTIMISÉES (vues matérialisées + filtrage in-memory)
    # ==========================================================================
    from src.database.base_queries import (
        get_kpis_global,
        get_yearly_stats_cached,
        get_cross_stats_cached,
        get_operations_base,
        get_cross_list_from_cache,
        CROSS_ACTIFS,
    )

    from src.utils.dataframe_filters import (
        filter_by_dates,
        filter_by_cross,
        compute_kpis,
        compute_by_cross,
        compute_by_type,
        compute_timeline,
        compute_bilan_humain,
    )

    # Anciennes fonctions (pour comparaison carte uniquement)
    from src.database.raw_queries import get_operations_dataframe

    # Dates par défaut
    if date_fin is None:
        date_fin = date.today()
    if date_debut is None:
        date_debut = date_fin - timedelta(days=365)

    results = PerformanceResults()

    # 1. Mesurer la latence DB
    latency = measure_db_latency(iterations=5)
    results.db_latency_avg_ms = latency["avg_ms"]
    results.db_latency_min_ms = latency["min_ms"]
    results.db_latency_max_ms = latency["max_ms"]
    results.db_latency_std_ms = latency["std_ms"]

    # ==========================================================================
    # 2. Définir les requêtes OPTIMISÉES à tester
    # ==========================================================================
    queries_to_test = [
        # Vues matérialisées (instantanées)
        ("get_kpis_global", get_kpis_global, [], {}),
        ("get_yearly_stats_cached", get_yearly_stats_cached, [], {}),
        ("get_cross_stats_cached", get_cross_stats_cached, [], {}),
        ("get_cross_list_from_cache", get_cross_list_from_cache, [], {}),
        # Chargement données de base (une seule fois, puis cache)
        ("get_operations_base", get_operations_base, [], {}),
        # Carte (toujours via raw_queries)
        ("get_operations_dataframe", get_operations_dataframe, [], {"date_debut": date_debut, "date_fin": date_fin, "limit": 1000}),
    ]

    # Essayer d'ajouter les KPIs avancés (cachés par Streamlit)
    try:
        from src.database.kpi_queries import (
            get_kpi_securite_global,
            get_kpi_yoy_latest,
        )
        queries_to_test.extend([
            ("get_kpi_securite_global", get_kpi_securite_global, [date_debut, date_fin], {"cross_actifs_seulement": True}),
            ("get_kpi_yoy_latest", get_kpi_yoy_latest, [], {"cross_actifs_seulement": True}),
        ])
    except ImportError:
        pass  # KPIs avancés non disponibles

    # 3. Invalider le cache si demandé
    if clear_cache:
        st.cache_data.clear()
        st.cache_resource.clear()

    # 4. Premier passage (sans cache) - Requêtes SQL
    first_pass_results = []
    df_base = None  # Stocker le DataFrame pour les tests in-memory

    for name, func, args, kwargs in queries_to_test:
        try:
            elapsed_ms, result, rows = _time_function(func, *args, **kwargs)
            first_pass_results.append({
                "name": name,
                "first_ms": elapsed_ms,
                "rows": rows,
                "error": None,
            })
            # Garder le DataFrame pour les tests in-memory
            if name == "get_operations_base" and isinstance(result, pd.DataFrame):
                df_base = result
        except Exception as e:
            first_pass_results.append({
                "name": name,
                "first_ms": 0,
                "rows": 0,
                "error": str(e),
            })

    # 5. Deuxième passage (avec cache)
    for i, (name, func, args, kwargs) in enumerate(queries_to_test):
        try:
            elapsed_ms, result, rows = _time_function(func, *args, **kwargs)
            first_pass_results[i]["cached_ms"] = elapsed_ms
            # Garder le DataFrame si pas encore stocké
            if name == "get_operations_base" and df_base is None and isinstance(result, pd.DataFrame):
                df_base = result
        except Exception as e:
            first_pass_results[i]["cached_ms"] = 0
            if not first_pass_results[i]["error"]:
                first_pass_results[i]["error"] = str(e)

    # ==========================================================================
    # 6. Tests des fonctions IN-MEMORY (filtrage instantané)
    # ==========================================================================
    if df_base is not None and not df_base.empty:
        # Test filtrage par dates
        def _test_filter_dates():
            return filter_by_dates(df_base, date_debut, date_fin)

        elapsed_ms, df_filtered, rows = _time_function(_test_filter_dates)
        first_pass_results.append({
            "name": "filter_by_dates (in-memory)",
            "first_ms": elapsed_ms,
            "cached_ms": elapsed_ms,  # Pas de cache, toujours rapide
            "rows": rows if isinstance(rows, int) else len(df_filtered) if df_filtered is not None else 0,
            "error": None,
        })

        # Test filtrage par CROSS
        if df_filtered is not None:
            def _test_filter_cross():
                return filter_by_cross(df_filtered, cross_actifs_only=True, cross_actifs=CROSS_ACTIFS)

            elapsed_ms, df_cross, rows = _time_function(_test_filter_cross)
            first_pass_results.append({
                "name": "filter_by_cross (in-memory)",
                "first_ms": elapsed_ms,
                "cached_ms": elapsed_ms,
                "rows": len(df_cross) if df_cross is not None else 0,
                "error": None,
            })

            # Test compute_kpis
            def _test_compute_kpis():
                return compute_kpis(df_cross if df_cross is not None else df_filtered)

            elapsed_ms, kpis, _ = _time_function(_test_compute_kpis)
            first_pass_results.append({
                "name": "compute_kpis (in-memory)",
                "first_ms": elapsed_ms,
                "cached_ms": elapsed_ms,
                "rows": 1,
                "error": None,
            })

            # Test compute_by_cross
            def _test_compute_by_cross():
                return compute_by_cross(df_cross if df_cross is not None else df_filtered)

            elapsed_ms, result, rows = _time_function(_test_compute_by_cross)
            first_pass_results.append({
                "name": "compute_by_cross (in-memory)",
                "first_ms": elapsed_ms,
                "cached_ms": elapsed_ms,
                "rows": len(result) if result is not None else 0,
                "error": None,
            })

            # Test compute_timeline
            def _test_compute_timeline():
                return compute_timeline(df_cross if df_cross is not None else df_filtered, "month")

            elapsed_ms, result, rows = _time_function(_test_compute_timeline)
            first_pass_results.append({
                "name": "compute_timeline (in-memory)",
                "first_ms": elapsed_ms,
                "cached_ms": elapsed_ms,
                "rows": len(result) if result is not None else 0,
                "error": None,
            })

    # 7. Compiler les résultats
    for r in first_pass_results:
        results.queries.append(QueryResult(
            name=r["name"],
            first_ms=r["first_ms"],
            cached_ms=r.get("cached_ms", 0),
            rows_returned=r["rows"],
            error=r.get("error"),
        ))

    results.total_first_ms = sum(q.first_ms for q in results.queries)
    results.total_cached_ms = sum(q.cached_ms for q in results.queries)

    return results


def quick_latency_test() -> str:
    """Test rapide de latence pour affichage dans l'UI.

    Returns:
        Message formaté avec le résultat
    """
    try:
        latency = measure_db_latency(iterations=3)
        avg = latency["avg_ms"]

        if avg < 20:
            emoji = "🟢"
            status = "Excellent"
        elif avg < 50:
            emoji = "🟢"
            status = "Bon"
        elif avg < 100:
            emoji = "🟡"
            status = "Acceptable"
        elif avg < 200:
            emoji = "🟠"
            status = "Lent"
        else:
            emoji = "🔴"
            status = "Très lent"

        return f"{emoji} {status} - Latence moyenne: {avg:.1f}ms"
    except Exception as e:
        return f"🔴 Erreur de connexion: {e}"

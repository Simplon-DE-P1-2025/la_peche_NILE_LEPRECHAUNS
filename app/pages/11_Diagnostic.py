"""Page de diagnostic des performances - SECMAR.

Cette page permet de:
- Tester la latence réseau vers la base de données
- Benchmarker toutes les requêtes du Dashboard
- Comparer les temps avec/sans cache Streamlit
- Obtenir des recommandations d'optimisation

Usage: Accessible via la sidebar Streamlit
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import date, timedelta

# Configuration du path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info

# Configuration de la page
st.set_page_config(
    page_title="Diagnostic Performance - SECMAR",
    page_icon="🔧",
    layout="wide",
)

# Authentification
if not login_required():
    st.stop()

show_user_info()

# En-tête
st.title("🔧 Diagnostic Performance")
st.caption("Analysez les performances de connexion et des requêtes")

# Import des outils de performance (après auth pour éviter erreurs si non connecté)
try:
    from src.utils.performance import (
        measure_db_latency,
        benchmark_dashboard_queries,
        quick_latency_test,
        PerformanceResults,
    )
    PERF_AVAILABLE = True
except ImportError as e:
    PERF_AVAILABLE = False
    st.error(f"Module de performance non disponible: {e}")
    st.stop()

# Variables de session pour stocker les résultats
if "perf_results" not in st.session_state:
    st.session_state.perf_results = None


# =============================================================================
# Section 1: Test de latence rapide
# =============================================================================
st.subheader("📡 Test de Latence Base de Donnees")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    Ce test mesure le temps de réponse de la base de données (ping SELECT 1).

    **Interprétation:**
    - 🟢 < 50ms : Excellent (connexion locale ou région proche)
    - 🟡 50-100ms : Acceptable (région éloignée)
    - 🟠 100-200ms : Lent (impact sur les performances)
    - 🔴 > 200ms : Très lent (optimisation requise)
    """)

with col2:
    if st.button("🏓 Tester la latence", use_container_width=True):
        with st.spinner("Test en cours..."):
            result = quick_latency_test()
        st.info(result)

# Test détaillé
with st.expander("📊 Test détaillé (10 mesures)"):
    if st.button("Lancer le test détaillé"):
        with st.spinner("Mesures en cours..."):
            latency = measure_db_latency(iterations=10)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Moyenne", f"{latency['avg_ms']:.1f} ms")
        col2.metric("Min", f"{latency['min_ms']:.1f} ms")
        col3.metric("Max", f"{latency['max_ms']:.1f} ms")
        col4.metric("Écart-type", f"{latency['std_ms']:.1f} ms")

        # Graphique des mesures
        df_latency = pd.DataFrame({
            "Mesure": range(1, len(latency["all_ms"]) + 1),
            "Latence (ms)": latency["all_ms"],
        })

        st.line_chart(df_latency.set_index("Mesure"))

st.divider()


# =============================================================================
# Section 2: Benchmark des requêtes Dashboard
# =============================================================================
st.subheader("📊 Benchmark Requetes Dashboard")

st.markdown("""
Ce benchmark teste toutes les requêtes utilisées par le Dashboard principal.
Il compare les temps **sans cache** (première exécution) et **avec cache** (deuxième exécution).

**Objectif:** Identifier les requêtes lentes et quantifier l'impact du cache Streamlit.
""")

# Options du benchmark
col1, col2, col3 = st.columns(3)

with col1:
    date_debut = st.date_input(
        "Date début",
        value=date.today() - timedelta(days=365),
        key="diag_date_debut",
    )

with col2:
    date_fin = st.date_input(
        "Date fin",
        value=date.today(),
        key="diag_date_fin",
    )

with col3:
    clear_cache = st.checkbox(
        "Invalider le cache avant le test",
        value=True,
        help="Recommandé pour un benchmark précis",
    )

# Bouton de lancement
if st.button("🚀 Lancer le benchmark complet", type="primary", use_container_width=True):
    progress_bar = st.progress(0, text="Initialisation...")

    with st.spinner("Benchmark en cours... (peut prendre 30-60 secondes)"):
        progress_bar.progress(10, text="Mesure de la latence DB...")

        try:
            results = benchmark_dashboard_queries(
                date_debut=date_debut,
                date_fin=date_fin,
                clear_cache=clear_cache,
            )
            st.session_state.perf_results = results
            progress_bar.progress(100, text="Terminé!")
        except Exception as e:
            st.error(f"Erreur lors du benchmark: {e}")
            st.session_state.perf_results = None

# Affichage des résultats
if st.session_state.perf_results:
    results = st.session_state.perf_results

    st.divider()
    st.subheader("📈 Resultats du Benchmark")

    # KPIs globaux
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        latency_emoji = {
            "excellent": "🟢",
            "bon": "🟢",
            "acceptable": "🟡",
            "lent": "🟠",
            "tres_lent": "🔴",
        }.get(results.latency_status, "⚪")

        st.metric(
            f"{latency_emoji} Latence DB",
            f"{results.db_latency_avg_ms:.1f} ms",
            help=f"Min: {results.db_latency_min_ms:.1f}ms, Max: {results.db_latency_max_ms:.1f}ms",
        )

    with col2:
        st.metric(
            "Requêtes testées",
            len(results.queries),
            help="Nombre de fonctions de requête testées",
        )

    with col3:
        color = "🔴" if results.total_first_ms > 2000 else "🟡" if results.total_first_ms > 1000 else "🟢"
        st.metric(
            f"{color} Total (sans cache)",
            f"{results.total_first_ms:.0f} ms",
            help="Temps total pour toutes les requêtes sans cache",
        )

    with col4:
        st.metric(
            "🟢 Total (avec cache)",
            f"{results.total_cached_ms:.0f} ms",
            help="Temps total pour toutes les requêtes avec cache",
        )

    # Tableau détaillé
    st.markdown("### Détail par requête")

    df_results = pd.DataFrame([
        {
            "Requête": q.name,
            "Sans cache (ms)": round(q.first_ms, 1),
            "Avec cache (ms)": round(q.cached_ms, 1),
            "Gain cache": f"{((q.first_ms - q.cached_ms) / q.first_ms * 100):.0f}%" if q.first_ms > 0 else "N/A",
            "Lignes": q.rows_returned,
            "Erreur": q.error or "",
        }
        for q in results.queries
    ])

    # Trier par temps sans cache (décroissant)
    df_results = df_results.sort_values("Sans cache (ms)", ascending=False)

    st.dataframe(
        df_results,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Sans cache (ms)": st.column_config.NumberColumn(format="%.1f"),
            "Avec cache (ms)": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    # Graphique de comparaison
    st.markdown("### Comparaison visuelle")

    import plotly.graph_objects as go

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Sans cache",
        x=[q.name for q in results.queries],
        y=[q.first_ms for q in results.queries],
        marker_color="#e74c3c",
    ))

    fig.add_trace(go.Bar(
        name="Avec cache",
        x=[q.name for q in results.queries],
        y=[q.cached_ms for q in results.queries],
        marker_color="#2ecc71",
    ))

    fig.update_layout(
        barmode="group",
        xaxis_tickangle=-45,
        height=400,
        yaxis_title="Temps (ms)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Recommandations
    st.divider()
    st.subheader("💡 Recommandations")

    for rec in results.recommendations:
        if "Excellent" in rec or "correctes" in rec.lower():
            st.success(rec)
        elif "Latence élevée" in rec or "Trop de requêtes" in rec or "Temps total élevé" in rec:
            st.warning(rec)
        else:
            st.info(rec)

    # Analyse détaillée
    with st.expander("📋 Analyse détaillée"):
        st.markdown(f"""
        ### Résumé de l'analyse

        **Latence réseau:**
        - Moyenne: {results.db_latency_avg_ms:.1f}ms
        - Écart-type: {results.db_latency_std_ms:.1f}ms
        - Status: {results.latency_status}

        **Impact calculé:**
        - Nombre de requêtes: {len(results.queries)}
        - Latence × Requêtes = {results.db_latency_avg_ms:.0f}ms × {len(results.queries)} = **{results.db_latency_avg_ms * len(results.queries):.0f}ms** (minimum théorique)
        - Temps réel sans cache: **{results.total_first_ms:.0f}ms**
        - Overhead requêtes: {results.total_first_ms - (results.db_latency_avg_ms * len(results.queries)):.0f}ms

        **Efficacité du cache:**
        - Temps sans cache: {results.total_first_ms:.0f}ms
        - Temps avec cache: {results.total_cached_ms:.0f}ms
        - Gain: **{((results.total_first_ms - results.total_cached_ms) / results.total_first_ms * 100):.1f}%**

        **Requêtes les plus lentes (sans cache):**
        """)

        top_slow = sorted(results.queries, key=lambda x: x.first_ms, reverse=True)[:5]
        for i, q in enumerate(top_slow, 1):
            st.markdown(f"{i}. `{q.name}`: {q.first_ms:.1f}ms ({q.rows_returned} lignes)")


# =============================================================================
# Section 3: Statut Vue Matérialisée
# =============================================================================
st.divider()
st.subheader("⚡ Optimisation Base de Donnees")

try:
    from src.database.connection import check_materialized_view_status, refresh_materialized_views

    view_status = check_materialized_view_status()

    col1, col2 = st.columns(2)

    with col1:
        if view_status["view_type"] == "MATERIALIZED":
            st.success(f"✅ operations_stats est une **VUE MATÉRIALISÉE** ({view_status['row_count']:,} lignes)")
            st.markdown("Les requêtes utilisent des données pré-calculées (rapide).")
        elif view_status["view_type"] == "REGULAR":
            st.error("❌ operations_stats est une **VUE NORMALE** (lent)")
            st.markdown("""
            **Problème:** La vue est recalculée à chaque requête, ce qui cause les 88 secondes de chargement.

            **Solution:** Exécuter le script d'optimisation ci-dessous.
            """)
        else:
            st.warning(f"⚠️ Statut inconnu: {view_status.get('error', view_status['view_type'])}")

    with col2:
        st.markdown("**Actions:**")

        if view_status["view_type"] == "MATERIALIZED":
            if st.button("🔄 Rafraîchir la vue matérialisée"):
                with st.spinner("Rafraîchissement en cours..."):
                    success = refresh_materialized_views()
                if success:
                    st.success("Vue rafraîchie!")
                else:
                    st.error("Erreur lors du rafraîchissement")

        st.markdown("---")
        st.markdown("**Script d'optimisation:**")
        st.code("psql $DATABASE_URL -f sql/optimize_performance.sql", language="bash")
        st.caption("Ce script convertit la vue normale en vue matérialisée.")

except ImportError as e:
    st.warning(f"Fonctions non disponibles: {e}")


# =============================================================================
# Section 4: Informations système
# =============================================================================
st.divider()
st.subheader("ℹ️ Informations Systeme")

with st.expander("Configuration base de données"):
    try:
        from src.config import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_SCHEMA

        # Masquer le mot de passe
        safe_url = DATABASE_URL
        if "@" in safe_url:
            parts = safe_url.split("@")
            user_pass = parts[0].split("://")[1]
            if ":" in user_pass:
                user = user_pass.split(":")[0]
                safe_url = safe_url.replace(user_pass, f"{user}:****")

        st.code(f"""
DATABASE_URL: {safe_url}
DB_SCHEMA: {DB_SCHEMA}
DB_POOL_SIZE: {DB_POOL_SIZE}
DB_MAX_OVERFLOW: {DB_MAX_OVERFLOW}
        """)
    except Exception as e:
        st.error(f"Impossible de lire la configuration: {e}")

with st.expander("Cache Streamlit"):
    st.markdown("""
    **Configuration actuelle:**
    - TTL par défaut: 3600 secondes (1 heure)
    - Type: `@st.cache_data` (sérialisé)

    **Actions:**
    """)

    if st.button("🗑️ Vider tout le cache"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Cache vidé avec succès")
        st.session_state.perf_results = None

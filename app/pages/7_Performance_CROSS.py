"""Page Performance CROSS - Benchmarking et ranking des CROSS.

Cette page affiche:
- Ranking des CROSS par taux de sauvetage
- Comparaison des durées d'intervention
- Radar chart multi-KPI par CROSS
- Distribution des durées (box plot)
- Table de benchmarking avec code couleur

Date: Janvier 2026
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Configuration du path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.database.kpi_queries import (
    get_kpi_cross_benchmark,
    get_kpi_cross_detail,
    get_kpi_cross_ranking,
)
from src.database.raw_queries import get_cross_list

# Configuration de la page
st.set_page_config(
    page_title="Performance CROSS - SECMAR", page_icon="🏆", layout="wide"
)

# Authentification
if not login_required():
    st.stop()

show_user_info()

# En-tête
st.title("🏆 Performance CROSS")
st.caption("Benchmarking et comparaison des Centres Régionaux Opérationnels")

# =============================================================================
# Filtres
# =============================================================================
with st.sidebar:
    st.subheader("🔍 Filtres")

    cross_list = ["Tous"] + get_cross_list()
    selected_cross = st.selectbox("Focus sur un CROSS", options=cross_list, index=0)
    filter_cross = None if selected_cross == "Tous" else selected_cross

    metric_ranking = st.selectbox(
        "Métrique de ranking",
        options=["sauvetage", "volume", "rapidite"],
        format_func=lambda x: {
            "sauvetage": "🏆 Taux saines et sauves",
            "volume": "📊 Volume d'opérations",
            "rapidite": "⏱️ Rapidité d'intervention",
        }[x],
    )

    # Toggle CROSS historiques
    inclure_cross_historiques = st.toggle(
        "Inclure CROSS historiques",
        value=False,
        help="Inclure les CROSS fermés (Adge, Guyane, La Réunion, Martinique, etc.)",
    )
    st.caption("Note: Inclure les CROSS historiques peut rallonger le chargement.")
    cross_actifs_only = not inclure_cross_historiques

# =============================================================================
# Récupération des données
# =============================================================================
benchmark_data = get_kpi_cross_benchmark(cross_filter=filter_cross, cross_actifs_seulement=cross_actifs_only)

if not benchmark_data:
    st.warning("Aucune donnée disponible. Vérifiez que les vues SQL sont créées.")
    st.stop()

df = pd.DataFrame(benchmark_data)

# =============================================================================
# KPIs globaux
# =============================================================================
st.subheader("📊 Vue d'ensemble")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("CROSS analysés", len(df), help="Nombre de CROSS avec données")

with col2:
    moy_sauvetage = (
        df["taux_saines_sauves"].mean() if "taux_saines_sauves" in df.columns else 0
    )
    st.metric(
        "Taux saines/sauves moyen",
        f"{moy_sauvetage:.1f}%",
        help="Moyenne nationale (définition SECMAR)",
    )

with col3:
    moy_duree = (
        df["duree_mediane_heures"].mean() if "duree_mediane_heures" in df.columns else 0
    )
    st.metric(
        "Durée médiane moyenne", f"{moy_duree:.1f}h", help="Médiane des interventions"
    )

with col4:
    total_ops = df["nb_operations"].sum() if "nb_operations" in df.columns else 0
    st.metric("Total opérations", f"{total_ops:,}".replace(",", " "))

st.divider()

# =============================================================================
# Ranking horizontal
# =============================================================================
st.subheader(
    f"🏅 Ranking par {{'sauvetage': 'Taux de sauvetage', 'volume': 'Volume', 'rapidite': 'Rapidité'}}[metric_ranking]"
)

ranking_data = get_kpi_cross_ranking(metric=metric_ranking, cross_filter=filter_cross, cross_actifs_seulement=cross_actifs_only)

if ranking_data:
    df_ranking = pd.DataFrame(ranking_data)

    # Déterminer la colonne de tri
    if metric_ranking == "sauvetage":
        sort_col = "taux_saines_sauves"
        color_col = "taux_saines_sauves"
        df_ranking = df_ranking.sort_values(sort_col, ascending=False)
    elif metric_ranking == "volume":
        sort_col = "nb_operations"
        color_col = "nb_operations"
        df_ranking = df_ranking.sort_values(sort_col, ascending=False)
    else:  # rapidite
        sort_col = "duree_mediane_heures"
        color_col = "duree_mediane_heures"
        df_ranking = df_ranking.sort_values(sort_col, ascending=True)

    # Bar chart horizontal
    fig_ranking = px.bar(
        df_ranking,
        y="cross_name",
        x=sort_col,
        orientation="h",
        color=color_col,
        color_continuous_scale=(
            "RdYlGn"
            if metric_ranking == "sauvetage"
            else "Blues" if metric_ranking == "volume" else "RdYlGn_r"
        ),
        labels={
            "cross_name": "CROSS",
            "taux_saines_sauves": "Taux saines/sauves (%)",
            "nb_operations": "Nb opérations",
            "duree_mediane_heures": "Durée médiane (h)",
        },
        title="",
    )
    fig_ranking.update_layout(
        height=max(400, len(df_ranking) * 35),
        yaxis={
            "categoryorder": (
                "total ascending"
                if metric_ranking != "rapidite"
                else "total descending"
            )
        },
        showlegend=False,
    )

    # Ligne de référence pour le taux saines et sauves (objectif SECMAR 98%)
    if metric_ranking == "sauvetage":
        fig_ranking.add_vline(
            x=98, line_dash="dash", line_color="green", annotation_text="Objectif 98%"
        )

    st.plotly_chart(fig_ranking, use_container_width=True)

st.divider()

# =============================================================================
# Radar Chart (si un CROSS est sélectionné)
# =============================================================================
if filter_cross and filter_cross != "Tous":
    st.subheader(f"🎯 Profil Multi-KPI: {filter_cross}")

    cross_detail = get_kpi_cross_detail(filter_cross, cross_actifs_seulement=cross_actifs_only)

    if cross_detail:
        # Normalisation des métriques pour le radar
        # On compare au max de chaque métrique dans le benchmark
        max_ops = df["nb_operations"].max()
        max_personnes = df["total_personnes"].max()
        max_saines_sauves = (
            df["total_saines_sauves"].max()
            if "total_saines_sauves" in df.columns
            else 1
        )

        # Calcul des scores normalisés (0-100)
        radar_data = {
            "Métrique": [
                "Volume ops",
                "Personnes",
                "Saines/Sauves",
                "Taux S&S",
                "Rapidité",
            ],
            "Score": [
                (cross_detail.get("nb_operations", 0) / max(max_ops, 1)) * 100,
                (cross_detail.get("total_personnes", 0) / max(max_personnes, 1)) * 100,
                (cross_detail.get("total_saines_sauves", 0) / max(max_saines_sauves, 1))
                * 100,
                cross_detail.get("taux_saines_sauves", 0) or 0,
                100
                - min(
                    (cross_detail.get("duree_mediane_heures", 0) or 0) * 10, 100
                ),  # Inverse pour rapidité
            ],
        }

        df_radar = pd.DataFrame(radar_data)

        fig_radar = go.Figure()

        fig_radar.add_trace(
            go.Scatterpolar(
                r=df_radar["Score"],
                theta=df_radar["Métrique"],
                fill="toself",
                name=filter_cross,
                line_color="#3498db",
            )
        )

        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=400,
        )

        col1, col2 = st.columns([1, 1])

        with col1:
            st.plotly_chart(fig_radar, use_container_width=True)

        with col2:
            st.markdown("#### Détail des métriques")
            st.markdown(
                f"""
            | Métrique | Valeur | Rank |
            |----------|--------|------|
            | Opérations | **{cross_detail.get('nb_operations', 0):,}** | #{cross_detail.get('rank_volume', '-')} |
            | Personnes impliquées | **{cross_detail.get('total_personnes', 0):,}** | - |
            | Saines et Sauves | **{cross_detail.get('total_saines_sauves', 0):,}** | - |
            | Taux S&S | **{cross_detail.get('taux_saines_sauves', 0) or 0:.1f}%** | #{cross_detail.get('rank_sauvetage', '-')} |
            | Durée médiane | **{cross_detail.get('duree_mediane_heures', 0) or 0:.1f}h** | #{cross_detail.get('rank_rapidite', '-')} |
            | Durée moyenne | **{cross_detail.get('duree_moyenne_heures', 0) or 0:.1f}h** | - |
            | Ops/jour | **{cross_detail.get('operations_par_jour', 0) or 0:.2f}** | - |
            """.replace(
                    ",", " "
                )
            )

    st.divider()

# =============================================================================
# Distribution des durées (Box Plot)
# =============================================================================
st.subheader("⏱️ Distribution des durées d'intervention")

col1, col2 = st.columns(2)

with col1:
    # Box plot des durées par CROSS
    fig_box = px.box(
        df,
        x="cross_name",
        y="duree_mediane_heures",
        points="all",
        title="Durée médiane par CROSS",
        labels={
            "cross_name": "CROSS",
            "duree_mediane_heures": "Durée médiane (heures)",
        },
        color="cross_name",
    )
    fig_box.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig_box, use_container_width=True)

with col2:
    # Scatter durée vs taux saines et sauves
    fig_scatter = px.scatter(
        df,
        x="duree_mediane_heures",
        y="taux_saines_sauves",
        size="nb_operations",
        color="cross_name",
        hover_name="cross_name",
        title="Durée vs Taux saines et sauves",
        labels={
            "duree_mediane_heures": "Durée médiane (h)",
            "taux_saines_sauves": "Taux saines/sauves (%)",
            "nb_operations": "Nb opérations",
        },
    )
    fig_scatter.add_hline(
        y=98, line_dash="dash", line_color="green", annotation_text="Obj. 98%"
    )
    fig_scatter.update_layout(height=400)
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# =============================================================================
# Tableau de benchmarking complet
# =============================================================================
st.subheader("📋 Tableau de benchmarking complet")

# Préparation des données pour affichage
df_display = df[
    [
        "cross_name",
        "nb_operations",
        "total_personnes",
        "total_saines_sauves",
        "taux_saines_sauves",
        "taux_mortalite",
        "duree_mediane_heures",
        "operations_par_jour",
        "rank_volume",
        "rank_sauvetage",
        "rank_rapidite",
    ]
].copy()

df_display.columns = [
    "CROSS",
    "Opérations",
    "Personnes",
    "S&S",
    "Taux S&S (%)",
    "Taux mort. (%)",
    "Durée méd. (h)",
    "Ops/jour",
    "Rank Vol.",
    "Rank S&S",
    "Rank Rap.",
]

# Tri par ranking saines et sauves
df_display = df_display.sort_values("Rank S&S")


# Fonction pour colorer les cellules
def highlight_performance(val, col):
    """Applique une couleur selon la performance."""
    if col == "Taux S&S (%)":
        if val >= 98:
            return "background-color: #d4edda"  # Vert
        elif val >= 95:
            return "background-color: #fff3cd"  # Jaune
        else:
            return "background-color: #f8d7da"  # Rouge
    elif col == "Taux mort. (%)":
        if val <= 1:
            return "background-color: #d4edda"
        elif val <= 3:
            return "background-color: #fff3cd"
        else:
            return "background-color: #f8d7da"
    return ""


st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Opérations": st.column_config.NumberColumn(format="%d"),
        "Personnes": st.column_config.NumberColumn(format="%d"),
        "S&S": st.column_config.NumberColumn(format="%d"),
        "Taux S&S (%)": st.column_config.NumberColumn(format="%.1f %%"),
        "Taux mort. (%)": st.column_config.NumberColumn(format="%.2f %%"),
        "Durée méd. (h)": st.column_config.NumberColumn(format="%.1f"),
        "Ops/jour": st.column_config.NumberColumn(format="%.2f"),
    },
)

# Export Excel
st.download_button(
    label="📥 Exporter en CSV",
    data=df_display.to_csv(index=False),
    file_name="benchmark_cross.csv",
    mime="text/csv",
)

# =============================================================================
# Footer
# =============================================================================
st.divider()
st.caption("🏆 Performance CROSS - Benchmarking SECMAR | Standards SAR internationaux")

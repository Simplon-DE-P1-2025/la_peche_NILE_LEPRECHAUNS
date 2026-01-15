"""Page KPI Sécurité Maritime - Monitoring des indicateurs de sécurité.

Cette page affiche:
- Taux de sauvetage, mortalité, disparition (avec objectifs)
- Lives Saved (cumul aligné USCG/IMO)
- Indice de gravité composite
- Evolution temporelle des indicateurs
- Heatmap de gravité par période
- Alertes sur dépassement de seuils

Date: Janvier 2026
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Configuration du path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.database.kpi_queries import (
    get_kpi_securite_global,
    get_kpi_securite_mensuel,
    get_kpi_lives_saved,
    get_kpi_yoy_comparison,
    get_kpi_alertes_actives,
)

# Configuration de la page
st.set_page_config(page_title="KPI Sécurité - SECMAR", page_icon="🛡️", layout="wide")

# Authentification
if not login_required():
    st.stop()

show_user_info()

# En-tête
st.title("🛡️ KPI Sécurité Maritime")
st.caption("Monitoring des indicateurs de sécurité - Standards USCG/IMO")

# =============================================================================
# Filtres
# =============================================================================
with st.sidebar:
    st.subheader("🔍 Filtres")

    annee_filter = st.selectbox(
        "Année",
        options=[None, 2024, 2023, 2022, 2021, 2020],
        format_func=lambda x: "Toutes" if x is None else str(x),
    )

    nb_mois = st.slider("Nombre de mois à afficher", 12, 60, 36)

    # Toggle CROSS historiques
    inclure_cross_historiques = st.toggle(
        "Inclure CROSS historiques",
        value=False,
        help="Inclure les CROSS fermés (Adge, Guyane, La Réunion, Martinique, etc.)",
    )
    cross_actifs_only = not inclure_cross_historiques

# =============================================================================
# KPIs principaux
# =============================================================================
st.subheader("📊 Indicateurs de Sécurité")

# Récupération des données
kpi_global = get_kpi_securite_global(cross_actifs_seulement=cross_actifs_only) or {}
lives_saved = get_kpi_lives_saved(annee_filter, cross_actifs_seulement=cross_actifs_only) or {}

# Ligne 1: KPIs Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    taux_sauv = kpi_global.get("taux_saines_sauves", 0) or 0
    # Objectif officiel SECMAR: >98%
    if taux_sauv >= 98:
        st.success(f"**Taux Saines et Sauves**")
        status = "🟢 Excellent"
    elif taux_sauv >= 95:
        st.warning(f"**Taux Saines et Sauves**")
        status = "🟡 Attention"
    else:
        st.error(f"**Taux Saines et Sauves**")
        status = "🔴 Critique"

    st.metric(
        label=status,
        value=f"{taux_sauv:.1f}%",
        delta=f"Objectif: 98%",
        delta_color="normal" if taux_sauv >= 98 else "inverse",
        help="KPI officiel SECMAR (Secourues + Assistées + Retrouvées) / Prises en compte",
    )

with col2:
    total_saines_sauves = lives_saved.get("saines_sauves", 0) or 0
    st.info("**Saines et Sauves**")
    st.metric(
        label="🏆 Total cumulé",
        value=f"{total_saines_sauves:,}".replace(",", " "),
        help="Définition SECMAR: Secourues + Assistées + Retrouvées",
    )

with col3:
    taux_mort = kpi_global.get("taux_mortalite", 0) or 0
    if taux_mort <= 1:
        st.success("**Taux de Mortalité**")
        status = "🟢 Normal"
    elif taux_mort <= 3:
        st.warning("**Taux de Mortalité**")
        status = "🟡 Élevé"
    else:
        st.error("**Taux de Mortalité**")
        status = "🔴 Critique"

    st.metric(
        label=status,
        value=f"{taux_mort:.2f}%",
        delta=f"Objectif: <1%",
        delta_color="inverse" if taux_mort > 1 else "normal",
    )

with col4:
    indice_grav = kpi_global.get("indice_gravite", 0) or 0
    if indice_grav <= 0.05:
        st.success("**Indice de Gravité**")
        status = "🟢 Faible"
    elif indice_grav <= 0.1:
        st.warning("**Indice de Gravité**")
        status = "🟡 Modéré"
    else:
        st.error("**Indice de Gravité**")
        status = "🔴 Élevé"

    st.metric(
        label=status,
        value=f"{indice_grav:.3f}",
        help="(Décédés×3 + Disparus×2 + Blessés) / Impliqués",
    )

st.divider()

# =============================================================================
# Gauge du Taux de Sauvetage
# =============================================================================
col_gauge, col_detail = st.columns([1, 2])

with col_gauge:
    st.markdown("### 🎯 Objectif Taux Saines et Sauves (SECMAR)")

    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=taux_sauv,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Taux Saines et Sauves (%)"},
            delta={"reference": 98, "position": "bottom", "suffix": " vs objectif"},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {
                    "color": (
                        "#2ecc71"
                        if taux_sauv >= 98
                        else "#f39c12" if taux_sauv >= 95 else "#e74c3c"
                    )
                },
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 95], "color": "#ffebee"},
                    {"range": [95, 98], "color": "#fff8e1"},
                    {"range": [98, 100], "color": "#e8f5e9"},
                ],
                "threshold": {
                    "line": {"color": "green", "width": 4},
                    "thickness": 0.75,
                    "value": 98,
                },
            },
        )
    )
    fig_gauge.update_layout(height=300, margin=dict(t=50, b=0, l=0, r=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_detail:
    st.markdown("### 📈 Détail du bilan humain")

    total_impliques = kpi_global.get("total_impliques", 0) or 0
    total_decedes = kpi_global.get("total_decedes", 0) or 0
    total_disparus = kpi_global.get("total_disparus", 0) or 0
    total_blesses = kpi_global.get("total_blesses", 0) or 0
    total_saines_sauves_g = kpi_global.get("total_saines_sauves", 0) or 0

    # Bilan en tableau
    df_bilan = pd.DataFrame(
        {
            "Catégorie": ["Saines et Sauves", "Blessés", "Décédés", "Disparus"],
            "Nombre": [
                total_saines_sauves_g,
                total_blesses,
                total_decedes,
                total_disparus,
            ],
            "Pourcentage": [
                f"{100*total_saines_sauves_g/max(total_impliques,1):.1f}%",
                f"{100*total_blesses/max(total_impliques,1):.1f}%",
                f"{100*total_decedes/max(total_impliques,1):.1f}%",
                f"{100*total_disparus/max(total_impliques,1):.1f}%",
            ],
        }
    )

    # Graphique en donut
    fig_donut = px.pie(
        df_bilan,
        values="Nombre",
        names="Catégorie",
        hole=0.5,
        color="Catégorie",
        color_discrete_map={
            "Saines et Sauves": "#2ecc71",
            "Blessés": "#f39c12",
            "Décédés": "#e74c3c",
            "Disparus": "#34495e",
        },
    )
    fig_donut.update_layout(height=300, margin=dict(t=20, b=0, l=0, r=0))
    fig_donut.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()

# =============================================================================
# Evolution mensuelle
# =============================================================================
st.subheader("📅 Evolution mensuelle des indicateurs")

data_mensuel = get_kpi_securite_mensuel(annee=annee_filter, limit=nb_mois, cross_actifs_seulement=cross_actifs_only)

if data_mensuel:
    df_mensuel = pd.DataFrame(data_mensuel)
    df_mensuel["periode"] = pd.to_datetime(df_mensuel["periode"])

    # Graphique multi-axes
    fig = go.Figure()

    # Taux saines et sauves (ligne principale)
    fig.add_trace(
        go.Scatter(
            x=df_mensuel["periode"],
            y=df_mensuel["taux_saines_sauves"],
            mode="lines+markers",
            name="Taux saines et sauves (%)",
            line=dict(color="#2ecc71", width=3),
            marker=dict(size=8),
            yaxis="y",
        )
    )

    # Ligne objectif 98% (SECMAR)
    fig.add_hline(
        y=98,
        line_dash="dash",
        line_color="green",
        annotation_text="Objectif 98%",
        annotation_position="right",
    )

    # Taux mortalité (axe secondaire)
    fig.add_trace(
        go.Scatter(
            x=df_mensuel["periode"],
            y=df_mensuel["taux_mortalite"],
            mode="lines+markers",
            name="Taux mortalité (%)",
            line=dict(color="#e74c3c", width=2),
            marker=dict(size=6),
            yaxis="y2",
        )
    )

    fig.update_layout(
        height=400,
        yaxis=dict(
            title="Taux saines et sauves (%)",
            range=[80, 100],
            side="left",
            showgrid=True,
        ),
        yaxis2=dict(
            title="Taux de mortalité (%)", overlaying="y", side="right", range=[0, 10]
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Heatmap de l'indice de gravité
    st.markdown("#### 🔥 Heatmap Indice de Gravité par mois")

    df_heatmap = df_mensuel.copy()
    df_heatmap["annee"] = df_heatmap["periode"].dt.year
    df_heatmap["mois"] = df_heatmap["periode"].dt.month

    pivot = df_heatmap.pivot_table(
        index="annee", columns="mois", values="indice_gravite", aggfunc="mean"
    )
    # Reindexer pour garantir tous les mois 1-12
    pivot = pivot.reindex(columns=range(1, 13))

    fig_heat = px.imshow(
        pivot,
        labels=dict(x="Mois", y="Année", color="Indice gravité"),
        x=[
            "Jan",
            "Fév",
            "Mar",
            "Avr",
            "Mai",
            "Jun",
            "Jul",
            "Aoû",
            "Sep",
            "Oct",
            "Nov",
            "Déc",
        ],
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
    )
    fig_heat.update_layout(height=250)
    st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.info("Pas de données disponibles pour la période sélectionnée")

st.divider()

# =============================================================================
# Comparatif Year-over-Year
# =============================================================================
st.subheader("📊 Comparatif Year-over-Year")

yoy_data = get_kpi_yoy_comparison(annee=annee_filter, limit=10, cross_actifs_seulement=cross_actifs_only)

if yoy_data:
    df_yoy = pd.DataFrame(yoy_data)

    col1, col2 = st.columns(2)

    with col1:
        fig_yoy = px.bar(
            df_yoy,
            x="annee",
            y=["total_saines_sauves", "total_decedes", "total_disparus"],
            barmode="group",
            title="Bilan humain par année",
            color_discrete_map={
                "total_saines_sauves": "#2ecc71",
                "total_decedes": "#e74c3c",
                "total_disparus": "#34495e",
            },
            labels={
                "value": "Nombre",
                "variable": "Catégorie",
                "annee": "Année",
                "total_saines_sauves": "Saines et Sauves",
            },
        )
        fig_yoy.update_layout(height=350)
        st.plotly_chart(fig_yoy, use_container_width=True)

    with col2:
        fig_taux = px.line(
            df_yoy,
            x="annee",
            y=["taux_saines_sauves", "taux_mortalite"],
            markers=True,
            title="Evolution des taux",
            labels={
                "value": "Taux (%)",
                "variable": "Indicateur",
                "annee": "Année",
                "taux_saines_sauves": "Taux saines et sauves",
            },
        )
        fig_taux.add_hline(
            y=98, line_dash="dash", line_color="green", annotation_text="Obj. 98%"
        )
        fig_taux.update_layout(height=350)
        st.plotly_chart(fig_taux, use_container_width=True)

    # Tableau YoY
    st.markdown("#### 📋 Tableau comparatif")
    df_display = df_yoy[
        [
            "annee",
            "nb_operations",
            "total_personnes",
            "total_saines_sauves",
            "taux_saines_sauves",
            "yoy_operations_pct",
            "yoy_sauves_pct",
        ]
    ].copy()
    df_display.columns = [
        "Année",
        "Opérations",
        "Personnes",
        "Saines/Sauves",
        "Taux (%)",
        "Var. ops (%)",
        "Var. S&S (%)",
    ]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

else:
    st.info("Pas de données YoY disponibles")

st.divider()

# =============================================================================
# Alertes actives
# =============================================================================
st.subheader("🚨 Alertes et Anomalies")

alertes = get_kpi_alertes_actives(annee=annee_filter, cross_actifs_seulement=cross_actifs_only)

if alertes:
    st.warning(f"**{len(alertes)} période(s) en alerte détectée(s)**")

    for alerte in alertes[:5]:  # Max 5 alertes affichées
        niveau_victimes = alerte.get("niveau_alerte_victimes", "NORMAL")
        niveau_ops = alerte.get("niveau_alerte_operations", "NORMAL")
        periode = alerte.get("periode")
        z_victimes = alerte.get("zscore_victimes", 0)
        z_ops = alerte.get("zscore_operations", 0)

        if niveau_victimes == "ALERTE":
            st.error(
                f"🔴 **{periode}** - Victimes: Z-score = {z_victimes:.2f} (>2.5 écarts-types)"
            )
        elif niveau_victimes == "ATTENTION":
            st.warning(
                f"🟡 **{periode}** - Victimes: Z-score = {z_victimes:.2f} (>1.5 écart-type)"
            )

        if niveau_ops == "ALERTE":
            st.error(
                f"🔴 **{periode}** - Opérations: Z-score = {z_ops:.2f} (>2.5 écarts-types)"
            )
        elif niveau_ops == "ATTENTION":
            st.warning(
                f"🟡 **{periode}** - Opérations: Z-score = {z_ops:.2f} (>1.5 écart-type)"
            )
else:
    st.success("✅ Aucune alerte active - Tous les indicateurs sont dans les normes")

# =============================================================================
# Footer
# =============================================================================
st.divider()
st.caption(
    "📊 KPI Sécurité Maritime - Définition officielle SECMAR (Programme 205) | Objectif: >98%"
)

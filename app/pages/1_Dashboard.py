"""Dashboard analytique - Statistiques des operations SECMAR.

Cette page affiche:
- KPIs principaux avec sparklines et indicateurs YoY
- Taux de sauvetage (Gauge) et Lives Saved
- Graphiques de repartition par CROSS et par type d'operation
- Evolution temporelle des operations
- Bilan humain global et par CROSS
- Statistiques annuelles avec tendances
- Carte des operations (si coordonnees disponibles)

L'approche utilise des requetes Raw SQL et les vues KPI pour de meilleures
performances sur les agregations complexes.

Date: Janvier 2026
Version: 2.0 - Enrichi avec KPIs avancés
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# =============================================================================
# Configuration du path pour imports
# =============================================================================
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.database.raw_queries import (
    get_kpis,
    get_kpis_by_period,
    get_operations_by_cross,
    get_operations_by_type,
    get_operations_timeline,
    get_bilan_by_period,
    get_bilan_by_cross_filtered,
    get_operations_dataframe,
    get_cross_list,
    get_yearly_stats,
    get_nb_cross,
)

# Import des KPIs avancés
try:
    from src.database.kpi_queries import (
        get_kpi_securite_global,
        get_kpi_lives_saved,
        get_kpi_yoy_latest,
        get_kpi_alertes_actives,
        get_kpi_securite_mensuel,
    )

    KPI_ADVANCED_AVAILABLE = True
except ImportError:
    KPI_ADVANCED_AVAILABLE = False


# =============================================================================
# Configuration de la page Streamlit
# =============================================================================
st.set_page_config(page_title="Dashboard SECMAR", page_icon="📊", layout="wide")


# =============================================================================
# Authentification
# =============================================================================
if not login_required():
    st.stop()

show_user_info()

# =============================================================================
# En-tete de la page
# =============================================================================
st.title("📊 Dashboard Analytique")
st.caption("Statistiques des operations de sauvetage maritime")


# =============================================================================
# Section: Filtres (sidebar)
# =============================================================================
with st.sidebar:
    st.subheader("🔍 Filtres")

    # Période
    col1, col2 = st.columns(2)
    with col1:
        date_debut = st.date_input("Date début", value=None, key="dash_date_debut")
    with col2:
        date_fin = st.date_input("Date fin", value=None, key="dash_date_fin")

    # CROSS
    cross_list = ["Tous"] + get_cross_list()
    selected_cross = st.selectbox("CROSS", options=cross_list, index=0)
    filter_cross = None if selected_cross == "Tous" else selected_cross

    # Toggle CROSS historiques
    inclure_cross_historiques = st.toggle(
        "Inclure CROSS historiques",
        value=False,
        help="Inclure les CROSS fermés (Adge, Guyane, La Réunion, Martinique, etc.)",
    )

    # Granularité
    granularity = st.selectbox(
        "Granularité temporelle",
        options=["day", "week", "month", "year"],
        index=2,
        format_func=lambda x: {
            "day": "Jour",
            "week": "Semaine",
            "month": "Mois",
            "year": "Année",
        }[x],
    )

# =============================================================================
# Section: KPIs principaux (enrichis)
# =============================================================================
st.subheader("📈 Indicateurs cles")

# Filtrage par CROSS actifs selon le toggle
cross_actifs_only = not inclure_cross_historiques
kpis_global = get_kpis(cross_actifs_seulement=cross_actifs_only)
kpis_periode = get_kpis_by_period(date_debut, date_fin, cross_actifs_seulement=cross_actifs_only)

# Récupération des KPIs avancés si disponibles
kpi_securite = {}
kpi_yoy = {}
if KPI_ADVANCED_AVAILABLE:
    try:
        kpi_securite = get_kpi_securite_global(date_debut, date_fin, cross_actifs_seulement=cross_actifs_only) or {}
        kpi_yoy = get_kpi_yoy_latest(cross_actifs_seulement=cross_actifs_only) or {}
    except Exception:
        pass

# Ligne 1: KPIs principaux avec variations YoY
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_ops = kpis_global.get("total_operations", 0)
    yoy_ops = kpi_yoy.get("yoy_operations_pct")
    delta_ops = f"{yoy_ops:+.1f}% YoY" if yoy_ops is not None else None
    st.metric(
        "Total opérations",
        f"{total_ops:,}".replace(",", " "),
        delta=delta_ops,
        help="Nombre total d'opérations enregistrées",
    )

with col2:
    ops_periode = kpis_periode.get("total_operations", 0)
    st.metric(
        "Période sélectionnée",
        f"{ops_periode:,}".replace(",", " "),
        help=f"Du {date_debut} au {date_fin}",
    )
with col3:
    nb_cross = get_nb_cross(actifs_seulement=not inclure_cross_historiques)
    label_cross = "CROSS (tous)" if inclure_cross_historiques else "CROSS actifs"
    help_cross = (
        "Tous les CROSS (incluant historiques)"
        if inclure_cross_historiques
        else "CROSS actuellement en activité"
    )
    st.metric(label_cross, nb_cross, help=help_cross)

with col4:
    total_personnes = kpis_global.get("total_personnes", 0)
    yoy_personnes = kpi_yoy.get("yoy_personnes_pct")
    delta_pers = f"{yoy_personnes:+.1f}% YoY" if yoy_personnes is not None else None
    st.metric(
        "Personnes impliquées",
        f"{total_personnes:,}".replace(",", " "),
        delta=delta_pers,
    )

with col5:
    duree = kpis_global.get("duree_moyenne", 0) or 0
    st.metric("Durée moyenne", f"{duree:.0f} min")

# Ligne 2: KPIs de sécurité (si disponibles)
if KPI_ADVANCED_AVAILABLE and kpi_securite:
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        taux_sauv = kpi_securite.get("taux_saines_sauves", 0) or 0
        # Couleur selon le taux (objectif officiel SECMAR: >98%)
        if taux_sauv >= 98:
            color = "🟢"
        elif taux_sauv >= 95:
            color = "🟡"
        else:
            color = "🔴"
        st.metric(
            f"{color} Taux saines et sauves",
            f"{taux_sauv:.1f}%",
            help="KPI officiel SECMAR - Personnes mises hors de danger / Prises en compte (Objectif: >98%)",
        )

    with col2:
        lives_saved = kpi_securite.get("total_saines_sauves", 0) or 0
        yoy_sauves = kpi_yoy.get("yoy_sauves_pct")
        delta_sauves = f"{yoy_sauves:+.1f}% YoY" if yoy_sauves is not None else None
        st.metric(
            "🏆 Saines et Sauves",
            f"{lives_saved:,}".replace(",", " "),
            delta=delta_sauves,
            help="Personnes secourues + assistées + retrouvées (définition SECMAR)",
        )

    with col3:
        taux_mort = kpi_securite.get("taux_mortalite", 0) or 0
        # Couleur inversée (plus bas = mieux)
        if taux_mort <= 1:
            color = "🟢"
        elif taux_mort <= 3:
            color = "🟡"
        else:
            color = "🔴"
        st.metric(
            f"{color} Taux mortalité",
            f"{taux_mort:.2f}%",
            help="Décédés / Personnes impliquées (Objectif: <1%)",
        )

    with col4:
        indice_grav = kpi_securite.get("indice_gravite", 0) or 0
        # Indice de gravité (0 = parfait)
        if indice_grav <= 0.05:
            color = "🟢"
        elif indice_grav <= 0.1:
            color = "🟡"
        else:
            color = "🔴"
        st.metric(
            f"{color} Indice gravité",
            f"{indice_grav:.3f}",
            help="(Décédés×3 + Disparus×2 + Blessés) / Impliqués",
        )

    # Gauge du taux de sauvetage
    with st.expander("📊 Jauge Taux de Sauvetage", expanded=False):
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=taux_sauv,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Taux de Sauvetage (%)"},
                delta={"reference": 95, "position": "bottom"},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1},
                    "bar": {
                        "color": (
                            "#2ecc71"
                            if taux_sauv >= 95
                            else "#f39c12" if taux_sauv >= 90 else "#e74c3c"
                        )
                    },
                    "steps": [
                        {"range": [0, 90], "color": "#ffcccc"},
                        {"range": [90, 95], "color": "#fff3cd"},
                        {"range": [95, 100], "color": "#d4edda"},
                    ],
                    "threshold": {
                        "line": {"color": "green", "width": 4},
                        "thickness": 0.75,
                        "value": 95,
                    },
                },
            )
        )
        fig_gauge.update_layout(height=250)
        st.plotly_chart(fig_gauge, use_container_width=True)

st.divider()

# =============================================================================
# Section: Graphiques de repartition
# =============================================================================
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🏢 Opérations par CROSS")

    data_cross = get_operations_by_cross(cross_actifs_seulement=cross_actifs_only)
    if data_cross:
        df_cross = pd.DataFrame(data_cross)

        fig = px.bar(
            df_cross,
            x="cross",
            y="total_operations",
            color="total_personnes",
            color_continuous_scale="Blues",
            labels={
                "cross": "CROSS",
                "total_operations": "Opérations",
                "total_personnes": "Personnes",
            },
            title="",
        )
        fig.update_layout(height=400, xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données disponibles")

with col_right:
    st.subheader("📋 Répartition par type")

    data_type = get_operations_by_type(cross_actifs_seulement=cross_actifs_only)
    if data_type:
        df_type = pd.DataFrame(data_type)

        fig = px.pie(
            df_type,
            values="total",
            names="type_operation",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
            title="",
        )
        fig.update_layout(height=400)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

        # Legende types d'operation
        st.caption("**Legende :** SAR = Vie humaine en danger | MAS = Assistance navires | SUR = Surete | POL = Pollution | DIV = Autres")
    else:
        st.info("Pas de données disponibles")

# =============================================================================
# Section: Evolution temporelle
# =============================================================================
st.subheader("📅 Evolution dans le temps")

data_timeline = get_operations_timeline(granularity, date_debut, date_fin, cross_actifs_seulement=cross_actifs_only)

if data_timeline:
    df_timeline = pd.DataFrame(data_timeline)
    df_timeline["periode"] = pd.to_datetime(df_timeline["periode"], utc=True)

    fig = go.Figure()

    # Ligne pour les opérations
    fig.add_trace(
        go.Scatter(
            x=df_timeline["periode"],
            y=df_timeline["total_operations"],
            mode="lines+markers",
            name="Opérations",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=6),
        )
    )

    # Barres pour les personnes (axe secondaire)
    fig.add_trace(
        go.Bar(
            x=df_timeline["periode"],
            y=df_timeline["total_personnes"],
            name="Personnes impliquées",
            marker_color="rgba(255, 127, 14, 0.5)",
            yaxis="y2",
        )
    )

    fig.update_layout(
        height=400,
        yaxis=dict(title="Nombre d'opérations", side="left"),
        yaxis2=dict(title="Personnes impliquées", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pas de données pour la période sélectionnée")

# =============================================================================
# Section: Bilan humain
# =============================================================================
st.subheader("👥 Bilan humain")

col1, col2 = st.columns([1, 2])

with col1:
    bilan = get_bilan_by_period(date_debut, date_fin, cross_actifs_seulement=cross_actifs_only)
    if bilan:
        st.markdown("#### Totaux globaux")

        # Métriques avec couleurs
        st.markdown(
            f"""
        | Résultat | Nombre |
        |----------|--------|
        | 🟢 Saines et Sauves | **{bilan.get('total_saines_sauves', 0):,}** |
        | └ Secourues | *{bilan.get('total_secourues', 0):,}* |
        | └ Assistées | *{bilan.get('total_assistees', 0):,}* |
        | └ Retrouvées | *{bilan.get('total_retrouvees', 0):,}* |
        | 🟠 Blessés | **{bilan.get('total_blesses', 0):,}** |
        | 🔴 Décédés | **{bilan.get('total_decedes', 0):,}** |
        | ⚫ Disparus | **{bilan.get('total_disparus', 0):,}** |
        """.replace(
                ",", " "
            )
        )
    else:
        st.info("Pas de données disponibles")

with col2:
    bilan_cross = get_bilan_by_cross_filtered(date_debut, date_fin, cross_actifs_seulement=cross_actifs_only)
    if bilan_cross:
        df_bilan = pd.DataFrame(bilan_cross)

        fig = px.bar(
            df_bilan,
            x="cross",
            y=["saines_sauves", "blesses", "decedes", "disparus"],
            barmode="stack",
            color_discrete_map={
                "saines_sauves": "#2ecc71",
                "blesses": "#f39c12",
                "decedes": "#e74c3c",
                "disparus": "#34495e",
            },
            labels={
                "value": "Nombre",
                "variable": "Résultat",
                "cross": "CROSS",
                "saines_sauves": "Saines et Sauves",
            },
            title="Bilan par CROSS",
        )
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données disponibles")

# =============================================================================
# Section: Statistiques annuelles
# =============================================================================
st.subheader("📆 Statistiques par annee")

yearly_stats = get_yearly_stats(cross_actifs_seulement=cross_actifs_only)
if yearly_stats:
    df_yearly = pd.DataFrame(yearly_stats)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.line(
            df_yearly,
            x="annee",
            y="total_operations",
            markers=True,
            title="Évolution du nombre d'opérations",
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df_yearly,
            x="annee",
            y="total_personnes",
            title="Personnes impliquées par année",
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# Section: Carte des operations
# =============================================================================
st.subheader("🗺️ Carte des operations")

df_map = get_operations_dataframe(
    cross=filter_cross, date_debut=date_debut, date_fin=date_fin, limit=1000
)

if not df_map.empty and "latitude" in df_map.columns and "longitude" in df_map.columns:
    # Filtrer les coordonnées valides
    df_map_valid = df_map.dropna(subset=["latitude", "longitude"])
    df_map_valid = df_map_valid[
        (df_map_valid["latitude"].between(-90, 90))
        & (df_map_valid["longitude"].between(-180, 180))
    ]

    if not df_map_valid.empty:
        fig = px.scatter_mapbox(
            df_map_valid,
            lat="latitude",
            lon="longitude",
            color="type_operation",
            size="nombre_impliques",
            hover_data=["date_heure_reception_alerte", "cross", "nombre_saines_sauves"],
            zoom=5,
            center={"lat": 46.5, "lon": -1.5},
            mapbox_style="open-street-map",
            title="",
            color_discrete_sequence=[
                "#e63946",
                "#f4a261",
                "#2a9d8f",
                "#9b59b6",
                "#1d3557",
            ],
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de coordonnées valides pour afficher la carte")
else:
    st.info("Pas de données géographiques disponibles")

# =============================================================================
# Section: Export des donnees
# =============================================================================
with st.expander("📥 Exporter les donnees"):
    if not df_map.empty:
        csv = df_map.to_csv(index=False)
        st.download_button(
            label="Télécharger en CSV",
            data=csv,
            file_name=f"secmar_operations_{date_debut}_{date_fin}.csv",
            mime="text/csv",
        )
    else:
        st.info("Pas de données à exporter")

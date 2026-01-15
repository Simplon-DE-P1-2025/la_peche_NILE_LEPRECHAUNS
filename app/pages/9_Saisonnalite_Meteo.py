"""Page Saisonnalité & Météo - Analyse des facteurs temporels et météorologiques.

Cette page affiche:
- Saisonnalité mensuelle (pics estivaux)
- Impact vacances scolaires et jours fériés
- Distribution par phase du jour
- Corrélation météo / gravité (vent, mer, marée)

Date: Janvier 2026
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path

# Configuration du path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.database.kpi_queries import (
    get_kpi_temporel_multidim,
    get_kpi_saisonnalite_mensuelle,
    get_kpi_phase_journee,
    get_kpi_impact_vacances,
    get_kpi_meteo_correlation,
    get_kpi_meteo_par_force_vent,
    get_kpi_meteo_par_etat_mer,
)

# Configuration de la page
st.set_page_config(
    page_title="Saisonnalité & Météo - SECMAR", page_icon="🌤️", layout="wide"
)

# Authentification
if not login_required():
    st.stop()

show_user_info()

# En-tête
st.title("🌤️ Saisonnalité & Météo")
st.caption("Analyse des facteurs temporels et météorologiques")

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

    # Toggle CROSS historiques
    inclure_cross_historiques = st.toggle(
        "Inclure CROSS historiques",
        value=False,
        help="Inclure les CROSS fermés (Adge, Guyane, La Réunion, Martinique, etc.)",
    )
    st.caption("Note: Inclure les CROSS historiques peut rallonger le chargement.")
    cross_actifs_only = not inclure_cross_historiques

# =============================================================================
# Onglets principaux
# =============================================================================
tab1, tab2 = st.tabs(["📅 Temporel", "🌊 Météo"])

# =============================================================================
# TAB 1: ANALYSE TEMPORELLE
# =============================================================================
with tab1:
    st.subheader("📆 Saisonnalité mensuelle")

    data_mensuel = get_kpi_saisonnalite_mensuelle(annee=annee_filter, cross_actifs_seulement=cross_actifs_only)

    if data_mensuel:
        df_mensuel = pd.DataFrame(data_mensuel)

        # Noms des mois
        mois_noms = [
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
        ]
        df_mensuel["nom_mois"] = df_mensuel["mois"].apply(
            lambda x: mois_noms[int(x) - 1] if x else ""
        )

        col1, col2 = st.columns(2)

        with col1:
            # Bar chart mensuel
            fig_mois = px.bar(
                df_mensuel,
                x="nom_mois",
                y="total_operations",
                color="total_victimes",
                color_continuous_scale="Reds",
                title="Opérations par mois",
                labels={
                    "nom_mois": "Mois",
                    "total_operations": "Opérations",
                    "total_victimes": "Victimes",
                },
            )
            fig_mois.update_layout(height=350)
            st.plotly_chart(fig_mois, use_container_width=True)

        with col2:
            # Polar chart (radar mensuel)
            fig_polar = go.Figure()

            fig_polar.add_trace(
                go.Scatterpolar(
                    r=df_mensuel["total_operations"].tolist(),
                    theta=df_mensuel["nom_mois"].tolist(),
                    fill="toself",
                    name="Opérations",
                    line_color="#3498db",
                )
            )

            fig_polar.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                title="Distribution circulaire par mois",
                height=350,
            )
            st.plotly_chart(fig_polar, use_container_width=True)

    st.divider()

    # Phase du jour
    st.subheader("🌅 Distribution par phase du jour")

    data_phase = get_kpi_phase_journee(annee=annee_filter, cross_actifs_seulement=cross_actifs_only)

    if data_phase:
        df_phase = pd.DataFrame(data_phase)

        col1, col2 = st.columns(2)

        with col1:
            fig_phase = px.pie(
                df_phase,
                values="total_operations",
                names="phase_journee",
                title="Opérations par phase du jour",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Sunset,
            )
            fig_phase.update_layout(height=350)
            st.plotly_chart(fig_phase, use_container_width=True)

        with col2:
            # Gravité par phase
            fig_grav = px.bar(
                df_phase,
                x="phase_journee",
                y="indice_gravite_moyen",
                color="indice_gravite_moyen",
                color_continuous_scale="RdYlGn_r",
                title="Indice de gravité par phase",
                labels={
                    "phase_journee": "Phase",
                    "indice_gravite_moyen": "Indice gravité",
                },
            )
            fig_grav.update_layout(height=350)
            st.plotly_chart(fig_grav, use_container_width=True)

    st.divider()

    # Impact vacances
    st.subheader("🏖️ Impact vacances scolaires")

    data_vacances = get_kpi_impact_vacances(annee=annee_filter, cross_actifs_seulement=cross_actifs_only)

    if data_vacances:
        df_vac = pd.DataFrame(data_vacances)
        df_vac["Période"] = df_vac["en_vacances"].apply(
            lambda x: "Vacances" if x else "Hors vacances"
        )

        col1, col2 = st.columns(2)

        with col1:
            fig_vac = px.bar(
                df_vac,
                x="Période",
                y="total_operations",
                color="Période",
                title="Opérations: Vacances vs Hors-vacances",
                color_discrete_map={"Vacances": "#e74c3c", "Hors vacances": "#3498db"},
            )
            fig_vac.update_layout(height=300)
            st.plotly_chart(fig_vac, use_container_width=True)

        with col2:
            # Comparatif en métriques
            for _, row in df_vac.iterrows():
                label = "En vacances" if row["en_vacances"] else "Hors vacances"
                st.metric(
                    f"{label} - Opérations",
                    f"{row['total_operations']:,}".replace(",", " "),
                )
                st.metric(
                    f"{label} - Moy. pers/op", f"{row['moy_personnes_par_op']:.1f}"
                )

# =============================================================================
# TAB 2: ANALYSE MÉTÉO
# =============================================================================
with tab2:
    st.subheader("💨 Impact de la force du vent (Beaufort)")

    data_vent = get_kpi_meteo_par_force_vent(annee=annee_filter, cross_actifs_seulement=cross_actifs_only)

    if data_vent:
        df_vent = pd.DataFrame(data_vent)

        col1, col2 = st.columns(2)

        with col1:
            fig_vent = px.bar(
                df_vent,
                x="vent_force",
                y="total_operations",
                color="taux_mortalite_moyen",
                color_continuous_scale="RdYlGn_r",
                title="Opérations par force de vent",
                labels={
                    "vent_force": "Force Beaufort",
                    "total_operations": "Opérations",
                },
            )
            fig_vent.update_layout(height=350)
            st.plotly_chart(fig_vent, use_container_width=True)

        with col2:
            fig_grav_vent = px.line(
                df_vent,
                x="vent_force",
                y="indice_gravite_moyen",
                markers=True,
                title="Indice de gravité vs Force du vent",
                labels={
                    "vent_force": "Force Beaufort",
                    "indice_gravite_moyen": "Indice gravité",
                },
            )
            fig_grav_vent.update_layout(height=350)
            st.plotly_chart(fig_grav_vent, use_container_width=True)

        # Legende Beaufort
        st.caption("💨 **Echelle Beaufort** : 0-3 Calme (0-19 km/h) | 4-5 Brise (20-38) | 6-7 Frais (39-61) | 8-9 Coup de vent (62-88) | 10-12 Tempete (>88)")

    st.divider()

    st.subheader("🌊 Impact de l'état de la mer (Douglas)")

    data_mer = get_kpi_meteo_par_etat_mer(annee=annee_filter, cross_actifs_seulement=cross_actifs_only)

    if data_mer:
        df_mer = pd.DataFrame(data_mer)

        col1, col2 = st.columns(2)

        with col1:
            fig_mer = px.bar(
                df_mer,
                x="mer_force",
                y="total_operations",
                color="taux_mortalite_moyen",
                color_continuous_scale="RdYlGn_r",
                title="Opérations par état de la mer",
                labels={"mer_force": "État Douglas", "total_operations": "Opérations"},
            )
            fig_mer.update_layout(height=350)
            st.plotly_chart(fig_mer, use_container_width=True)

        with col2:
            fig_grav_mer = px.line(
                df_mer,
                x="mer_force",
                y="indice_gravite_moyen",
                markers=True,
                title="Indice de gravité vs État de la mer",
                labels={
                    "mer_force": "État Douglas",
                    "indice_gravite_moyen": "Indice gravité",
                },
            )
            fig_grav_mer.update_layout(height=350)
            st.plotly_chart(fig_grav_mer, use_container_width=True)

        # Legende Douglas
        st.caption("🌊 **Echelle Douglas** : 0-2 Calme (0-0.5m) | 3-4 Agitee (0.5-2.5m) | 5-6 Forte (2.5-6m) | 7-9 Grosse (>6m)")

    st.divider()

    # Heatmap Vent x Mer
    st.subheader("🔥 Corrélation Vent × Mer")

    data_corr = get_kpi_meteo_correlation(annee=annee_filter, cross_actifs_seulement=cross_actifs_only)

    if data_corr:
        df_corr = pd.DataFrame(data_corr)

        # Pivot pour heatmap
        pivot = df_corr.pivot_table(
            index="vent_force",
            columns="mer_force",
            values="indice_gravite",
            aggfunc="mean",
        )

        if not pivot.empty:
            fig_heat = px.imshow(
                pivot,
                labels=dict(
                    x="État mer (Douglas)", y="Vent (Beaufort)", color="Indice gravité"
                ),
                color_continuous_scale="RdYlGn_r",
                title="Matrice Vent × Mer → Gravité",
            )
            fig_heat.update_layout(height=400)
            st.plotly_chart(fig_heat, use_container_width=True)

            # Legendes combinées
            col_leg1, col_leg2 = st.columns(2)
            with col_leg1:
                st.caption("💨 Beaufort: 0-3 Calme | 4-5 Brise | 6-7 Frais | 8-9 Coup de vent | 10-12 Tempete")
            with col_leg2:
                st.caption("🌊 Douglas: 0-2 Calme | 3-4 Agitee | 5-6 Forte | 7-9 Grosse")

# Footer
st.divider()
st.caption("🌤️ Saisonnalité & Météo - Données SECMAR")

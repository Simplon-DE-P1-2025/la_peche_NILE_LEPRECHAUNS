"""Page Analyse Flotteurs - Statistiques par type d'embarcation.

Cette page affiche:
- Répartition par catégorie de flotteur
- Focus pêche professionnelle vs plaisance
- Sports nautiques émergents (kitesurf, wingfoil, etc.)
- Taux de mortalité par type de flotteur

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
    get_kpi_flotteurs_analyse,
    get_kpi_flotteurs_par_categorie,
    get_kpi_flotteurs_sports_nautiques,
)

# Configuration de la page
st.set_page_config(
    page_title="Analyse Flotteurs - SECMAR", page_icon="🚢", layout="wide"
)

# Authentification
if not login_required():
    st.stop()

show_user_info()

# En-tête
st.title("🚢 Analyse par Type de Flotteur")
st.caption("Statistiques sectorielles - Pêche, Plaisance, Sports nautiques")

# =============================================================================
# Filtres
# =============================================================================
with st.sidebar:
    st.subheader("🔍 Filtres")

    categories = ["Toutes", "Pêche", "Plaisance", "Commerce", "Loisir nautique"]
    selected_cat = st.selectbox("Catégorie", options=categories)
    filter_cat = None if selected_cat == "Toutes" else selected_cat

    # Toggle CROSS historiques
    inclure_cross_historiques = st.toggle(
        "Inclure CROSS historiques",
        value=False,
        help="Inclure les CROSS fermés (Adge, Guyane, La Réunion, Martinique, etc.)",
    )
    cross_actifs_only = not inclure_cross_historiques

# =============================================================================
# Récupération des données
# =============================================================================
data_categorie = get_kpi_flotteurs_par_categorie(categorie=filter_cat, cross_actifs_seulement=cross_actifs_only)
data_detail = get_kpi_flotteurs_analyse(categorie=filter_cat, limit=50, cross_actifs_seulement=cross_actifs_only)
data_sports = get_kpi_flotteurs_sports_nautiques(categorie=filter_cat, cross_actifs_seulement=cross_actifs_only)

if not data_categorie:
    st.warning("Aucune donnée disponible. Vérifiez que les vues SQL sont créées.")
    st.stop()

df_cat = pd.DataFrame(data_categorie)
df_detail = pd.DataFrame(data_detail) if data_detail else pd.DataFrame()
df_sports = pd.DataFrame(data_sports) if data_sports else pd.DataFrame()

# =============================================================================
# KPIs par catégorie
# =============================================================================
st.subheader("📊 Répartition par catégorie")

col1, col2 = st.columns(2)

with col1:
    # Pie chart des catégories
    fig_pie = px.pie(
        df_cat,
        values="total_operations",
        names="categorie_flotteur",
        title="Opérations par catégorie",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # Bar chart taux de mortalité par catégorie
    fig_bar = px.bar(
        df_cat,
        x="categorie_flotteur",
        y="taux_mortalite",
        color="taux_saines_sauves",
        color_continuous_scale="RdYlGn",
        title="Taux de mortalité par catégorie",
        labels={
            "categorie_flotteur": "Catégorie",
            "taux_mortalite": "Taux mortalité (%)",
            "taux_saines_sauves": "Taux saines/sauves",
        },
    )
    fig_bar.update_layout(height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# =============================================================================
# Tableau par catégorie
# =============================================================================
st.subheader("📋 Détail par catégorie")

df_cat_display = df_cat[
    [
        "categorie_flotteur",
        "total_operations",
        "total_personnes",
        "total_saines_sauves",
        "total_decedes",
        "taux_saines_sauves",
        "taux_mortalite",
        "distance_cote_moyenne_m",
    ]
].copy()

df_cat_display.columns = [
    "Catégorie",
    "Opérations",
    "Personnes",
    "S&S",
    "Décédés",
    "Taux S&S (%)",
    "Taux mort. (%)",
    "Dist. côte (m)",
]

st.dataframe(df_cat_display, use_container_width=True, hide_index=True)

st.divider()

# =============================================================================
# Sunburst Catégorie > Type > Résultat
# =============================================================================
if not df_detail.empty:
    st.subheader("🌳 Hiérarchie Catégorie → Type → Résultat")

    # Préparation pour sunburst
    df_sun = (
        df_detail.groupby(["categorie_flotteur", "type_flotteur", "resultat_flotteur"])
        .agg({"nb_operations": "sum"})
        .reset_index()
    )

    fig_sun = px.sunburst(
        df_sun,
        path=["categorie_flotteur", "type_flotteur", "resultat_flotteur"],
        values="nb_operations",
        color="nb_operations",
        color_continuous_scale="Blues",
        title="Répartition hiérarchique",
    )
    fig_sun.update_layout(height=500)
    st.plotly_chart(fig_sun, use_container_width=True)

st.divider()

# =============================================================================
# Focus Sports Nautiques
# =============================================================================
st.subheader("🏄 Focus Sports Nautiques Émergents")

if not df_sports.empty:
    col1, col2 = st.columns(2)

    with col1:
        # Bar chart sports nautiques
        fig_sports = px.bar(
            df_sports,
            x="type_flotteur",
            y="nb_operations",
            color="taux_mortalite",
            color_continuous_scale="RdYlGn_r",
            title="Opérations par sport nautique",
            labels={
                "type_flotteur": "Type",
                "nb_operations": "Opérations",
                "taux_mortalite": "Taux mortalité",
            },
        )
        fig_sports.update_layout(height=350)
        st.plotly_chart(fig_sports, use_container_width=True)

    with col2:
        # Métriques clés
        st.markdown("#### Indicateurs sports nautiques")

        total_ops_sports = df_sports["nb_operations"].sum()
        total_pers_sports = df_sports["total_personnes"].sum()
        total_deces_sports = df_sports["total_decedes"].sum()

        st.metric("Total opérations", f"{total_ops_sports:,}".replace(",", " "))
        st.metric("Personnes impliquées", f"{total_pers_sports:,}".replace(",", " "))
        st.metric("Décès", f"{total_deces_sports:,}".replace(",", " "))

        if total_pers_sports > 0:
            taux = (total_deces_sports / total_pers_sports) * 100
            st.metric("Taux mortalité sports", f"{taux:.2f}%")
else:
    st.info("Pas de données sports nautiques disponibles")

# =============================================================================
# Export
# =============================================================================
st.divider()

with st.expander("📥 Exporter les données"):
    csv = df_detail.to_csv(index=False) if not df_detail.empty else ""
    st.download_button(
        label="Télécharger en CSV",
        data=csv,
        file_name="analyse_flotteurs.csv",
        mime="text/csv",
    )

# Footer
st.caption("🚢 Analyse Flotteurs - Données SECMAR")

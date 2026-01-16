"""Page Carte des Catégories de Personnes - Visualisation géographique.

Cette page affiche:
- Carte interactive des opérations par catégorie de personne
- Filtres par catégorie (Migrant, Plaisancier, etc.)
- KPIs par catégorie avec taux de sauvetage
- Évolution temporelle par catégorie

Note sur la terminologie:
"Migrant" est descriptif et factuel dans les rapports CROSS/PRÉMAR : il désigne
des personnes en situation de vulnérabilité maritime, sans jugement moral ou juridique.
L'évolution terminologique (post-2021, SeaMIS) reflète une sensibilité accrue aux
droits humains, tout en préservant l'obligation de sauvetage.

Date: Janvier 2026
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import folium
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium
import sys
from pathlib import Path

# Configuration du path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.database.kpi_queries import (
    get_kpi_comptage_categorie,
    get_kpi_taux_sauvetage_categorie,
    get_kpi_evolution_categorie,
    get_kpi_cross_categorie,
    get_carte_operations_categorie,
)
from src.database.enums import CATEGORIE_PERSONNE

# Groupes de categories pour filtrage rapide de la carte
MAP_CATEGORY_GROUPS = {
    "Migrant/Clandestin": ["Migrant", "Clandestin", "Migrant/Clandestin"],
    "Plaisancier/Loisirs": ["Plaisancier français", "Pratiquant loisirs nautiques"],
    "Pêcheur": ["Pêcheur français", "Pêcheur amateur"],
    "Commerce": ["Commerce français"],
    "Marin étranger": ["Marin étranger"],
    "Autre/Non renseigné": ["Autre", "Non renseigné", "Toutes catégories"],
}

# Bounding boxes pour filtrage géographique SQL (optimisation performance)
ZONES_BBOX = {
    "France métropolitaine": {"lat_min": 41, "lat_max": 51.5, "lon_min": -5.5, "lon_max": 10},
    "Manche / Mer du Nord": {"lat_min": 48, "lat_max": 52, "lon_min": -2, "lon_max": 5},
    "Atlantique": {"lat_min": 43, "lat_max": 48, "lon_min": -6, "lon_max": 0},
    "Méditerranée": {"lat_min": 41, "lat_max": 44, "lon_min": 3, "lon_max": 10},
    "Antilles-Guyane": {"lat_min": 2, "lat_max": 18, "lon_min": -64, "lon_max": -50},
    "Réunion / Mayotte": {"lat_min": -25, "lat_max": -10, "lon_min": 40, "lon_max": 60},
    "Polynésie / Nouvelle-Calédonie": {"lat_min": -25, "lat_max": -10, "lon_min": 155, "lon_max": 180},
    "Monde entier": None,  # Pas de filtre géographique
}


# =============================================================================
# Fonctions cachées pour performance
# =============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_comptage_categorie(annee):
    """Charge les données de comptage par catégorie (caché 1h)."""
    return get_kpi_comptage_categorie(annee=annee)


@st.cache_data(ttl=3600, show_spinner=False)
def load_taux_sauvetage_categorie(annee):
    """Charge les taux de sauvetage par catégorie (caché 1h)."""
    return get_kpi_taux_sauvetage_categorie(annee=annee)


@st.cache_data(ttl=3600, show_spinner=False)
def load_carte_data(categorie, bbox=None, limit=10000):
    """Charge les données géographiques filtrées par zone (caché 1h).

    Args:
        categorie: Catégorie de personne à filtrer
        bbox: Dictionnaire avec lat_min, lat_max, lon_min, lon_max (ou None)
        limit: Nombre maximum de points à récupérer
    """
    if bbox:
        return get_carte_operations_categorie(
            categorie=categorie,
            lat_min=bbox.get("lat_min"),
            lat_max=bbox.get("lat_max"),
            lon_min=bbox.get("lon_min"),
            lon_max=bbox.get("lon_max"),
            limit=limit,
        )
    return get_carte_operations_categorie(categorie=categorie, limit=limit)


@st.cache_data(ttl=3600, show_spinner=False)
def load_cross_categorie(categorie):
    """Charge les données CROSS par catégorie (caché 1h)."""
    return get_kpi_cross_categorie(categorie=categorie)

# Configuration de la page
st.set_page_config(
    page_title="Carte Catégories - SECMAR",
    page_icon="🗺️",
    layout="wide"
)

# Authentification
if not login_required():
    st.stop()

show_user_info()

# En-tête
st.title("🗺️ Carte des Catégories de Personnes")
st.caption("Visualisation géographique des opérations par catégorie de personne")

# Note sur Migrant/Clandestin
with st.expander("ℹ️ Note sur la terminologie Migrant"):
    st.markdown("""
    **Évolution terminologique SECMAR → SeaMIS (2021)**

    Le terme **« Migrant »** est descriptif et factuel dans les rapports CROSS/PRÉMAR :
    il désigne simplement des personnes en situation de vulnérabilité maritime, sans
    jugement moral ou juridique, contrairement à « clandestin » qui évoque directement
    l'illégalité.

    Cette évolution (post-2021) suit la modernisation technique (SeaMIS) et une
    sensibilité accrue aux droits humains, tout en permettant des statistiques
    cohérentes sur un phénomène en hausse (+19% d'opérations en 2024).

    **Choix pragmatique** pour la coordination interservices et internationale,
    préservant l'obligation de sauvetage sans anticiper le traitement administratif
    ultérieur (OQTF, asile, etc.).

    | Aspect | Données |
    |--------|---------|
    | **CROSS principal** | Gris-Nez (81.5%), puis Réunion/Mayotte |
    | **Taux de sauvetage** | > 99% (performances excellentes) |
    """)

# =============================================================================
# Filtres
# =============================================================================
with st.sidebar:
    st.subheader("🔍 Filtres")

    # Liste des catégories avec "Toutes" en premier
    categories_options = ["Toutes"] + CATEGORIE_PERSONNE

    categorie_filter = st.selectbox(
        "Catégorie de personne",
        options=categories_options,
        index=0,
        help="Filtrer par catégorie de personne"
    )

    annee_filter = st.selectbox(
        "Année",
        options=[None, 2025, 2024, 2023, 2022, 2021, 2020, 2019],
        format_func=lambda x: "Toutes" if x is None else str(x),
    )

    # Option pour regrouper Migrant et Clandestin
    regrouper_migrants = st.toggle(
        "Regrouper Migrant + Clandestin",
        value=True,
        help="Traiter ces deux catégories comme une seule (recommandé)"
    )

    st.divider()
    st.subheader("🗺️ Zone géographique")

    # Sélection de la zone pour la carte
    zone_carte = st.selectbox(
        "Afficher",
        options=[
            "France métropolitaine",
            "Manche / Mer du Nord",
            "Atlantique",
            "Méditerranée",
            "Antilles-Guyane",
            "Réunion / Mayotte",
            "Polynésie / Nouvelle-Calédonie",
            "Monde entier"
        ],
        index=0,
        help="Sélectionner la zone à afficher sur la carte"
    )

    st.subheader("🎯 Catégories carte")
    selected_map_groups = st.multiselect(
        "Filtrer la carte",
        options=list(MAP_CATEGORY_GROUPS.keys()),
        default=list(MAP_CATEGORY_GROUPS.keys()),
        help="Filtre rapide par grands groupes de catégories"
    )
    map_allowed_categories = sorted({
        categorie
        for group in selected_map_groups
        for categorie in MAP_CATEGORY_GROUPS[group]
    })

    max_points = st.slider(
        "Nombre maximum de points",
        min_value=500,
        max_value=30000,
        value=5000,
        step=1000,
        help="Limiter le nombre de points affichés pour garder la carte fluide"
    )

    # Coordonnées de centrage par zone
    ZONES_GEO = {
        "France métropolitaine": {"center": [46.5, 2.5], "zoom": 5},
        "Manche / Mer du Nord": {"center": [50.5, 1.5], "zoom": 7},
        "Atlantique": {"center": [46.0, -3.0], "zoom": 6},
        "Méditerranée": {"center": [42.5, 6.5], "zoom": 6},
        "Antilles-Guyane": {"center": [14.5, -61.0], "zoom": 6},
        "Réunion / Mayotte": {"center": [-15.0, 50.0], "zoom": 5},
        "Polynésie / Nouvelle-Calédonie": {"center": [-18.0, 165.0], "zoom": 4},
        "Monde entier": {"center": [20.0, 0.0], "zoom": 2},
    }

# Convertir le filtre
cat_filter = None if categorie_filter == "Toutes" else categorie_filter

# =============================================================================
# KPIs par Catégorie
# =============================================================================
st.subheader("📊 Répartition par Catégorie")

# Récupération des données (avec cache Streamlit)
comptage = load_comptage_categorie(annee=annee_filter)
taux_sauvetage = load_taux_sauvetage_categorie(annee=annee_filter)

if comptage:
    df_comptage = pd.DataFrame(comptage)

    # Regroupement optionnel Migrant/Clandestin
    if regrouper_migrants and 'categorie_personne' in df_comptage.columns:
        df_comptage['categorie_personne'] = df_comptage['categorie_personne'].replace(
            {'Clandestin': 'Migrant/Clandestin', 'Migrant': 'Migrant/Clandestin'}
        )
        df_comptage = df_comptage.groupby(['categorie_personne', 'annee'], as_index=False).sum()

    # Graphique circulaire
    col1, col2 = st.columns(2)

    with col1:
        # Agrégation par catégorie
        df_pie = df_comptage.groupby('categorie_personne', as_index=False).agg({
            'total_personnes': 'sum',
            'nb_operations': 'sum'
        })
        df_pie = df_pie.sort_values('total_personnes', ascending=False)

        fig_pie = px.pie(
            df_pie,
            values='total_personnes',
            names='categorie_personne',
            title='Répartition des personnes par catégorie',
            hole=0.4,
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Taux de sauvetage par catégorie
        if taux_sauvetage:
            df_taux = pd.DataFrame(taux_sauvetage)

            if regrouper_migrants and 'categorie_personne' in df_taux.columns:
                df_taux['categorie_personne'] = df_taux['categorie_personne'].replace(
                    {'Clandestin': 'Migrant/Clandestin', 'Migrant': 'Migrant/Clandestin'}
                )
                df_taux = df_taux.groupby('categorie_personne', as_index=False).agg({
                    'nombre_saines_sauves': 'sum',
                    'nombre_prises_en_compte': 'sum',
                    'nombre_decedes': 'sum',
                    'nombre_disparus': 'sum',
                    'nombre_impliques': 'sum'
                })
                df_taux['taux_saines_sauves'] = (
                    df_taux['nombre_saines_sauves'] / df_taux['nombre_prises_en_compte'].replace(0, 1) * 100
                ).round(2)

            # Barchart horizontal des taux
            df_taux_sorted = df_taux.sort_values('taux_saines_sauves', ascending=True)

            fig_bar = px.bar(
                df_taux_sorted,
                x='taux_saines_sauves',
                y='categorie_personne',
                orientation='h',
                title='Taux de sauvetage par catégorie (%)',
                color='taux_saines_sauves',
                color_continuous_scale='RdYlGn',
            )
            fig_bar.add_vline(x=98, line_dash="dash", line_color="green", annotation_text="Objectif 98%")
            st.plotly_chart(fig_bar, use_container_width=True)

# =============================================================================
# Carte Géographique
# =============================================================================
st.subheader("🗺️ Carte Géographique")

# Récupération des données géographiques avec filtrage par zone (optimisé)
zone_bbox = ZONES_BBOX.get(zone_carte)
carte_data = load_carte_data(categorie=cat_filter, bbox=zone_bbox, limit=max_points)

if carte_data:
    df_carte = pd.DataFrame(carte_data)

    # Filtrer les données avec coordonnées valides
    df_carte = df_carte.dropna(subset=['latitude', 'longitude'])
    df_carte = df_carte[
        (df_carte['latitude'].between(-90, 90)) &
        (df_carte['longitude'].between(-180, 180))
    ]

    if not df_carte.empty:
        # Couleurs par catégorie
        couleurs = {
            'Migrant': 'red',
            'Clandestin': 'darkred',
            'Migrant/Clandestin': 'red',
            'Plaisancier français': 'blue',
            'Pratiquant loisirs nautiques': 'cyan',
            'Pêcheur français': 'green',
            'Pêcheur amateur': 'lightgreen',
            'Commerce français': 'orange',
            'Marin étranger': 'purple',
            'Autre': 'gray',
            'Toutes catégories': 'black',
            'Non renseigné': 'lightgray',
        }

        # Regroupement optionnel
        if regrouper_migrants and 'categorie_personne' in df_carte.columns:
            df_carte['categorie_personne'] = df_carte['categorie_personne'].replace(
                {'Clandestin': 'Migrant/Clandestin', 'Migrant': 'Migrant/Clandestin'}
            )

        if map_allowed_categories:
            df_carte = df_carte[df_carte['categorie_personne'].isin(map_allowed_categories)]
        else:
            df_carte = df_carte.iloc[0:0]

        # Note: Le LIMIT est déjà appliqué côté SQL, pas besoin de sampling Python
        nb_points = len(df_carte)
        if nb_points > 0:
            st.caption(f"Affichage de {nb_points:,} opérations (limite: {max_points:,})")

        # Création de la carte Folium avec zone sélectionnée
        zone_config = ZONES_GEO.get(zone_carte, ZONES_GEO["France métropolitaine"])

        m = folium.Map(
            location=zone_config["center"],
            zoom_start=zone_config["zoom"],
            tiles='CartoDB positron'
        )

        # Préparation des données pour FastMarkerCluster (optimisé)
        # Format: [lat, lon, popup_html, color, nb_personnes]
        marker_data = []
        for row in df_carte.itertuples(index=False):
            cat = getattr(row, 'categorie_personne', 'Autre') or 'Autre'
            color = couleurs.get(cat, 'gray')
            nb_personnes = getattr(row, 'nb_personnes', 0) or 0
            cross_name = getattr(row, 'cross_name', 'N/A') or 'N/A'
            operation_id = getattr(row, 'operation_id', 'N/A') or 'N/A'

            popup_html = f"<b>{cat}</b><br>CROSS: {cross_name}<br>Op: {operation_id}<br>Pers: {nb_personnes:,}"

            marker_data.append([
                row.latitude,
                row.longitude,
                popup_html,
                color,
                nb_personnes,
            ])

        # FastMarkerCluster avec callback JavaScript pour le rendu des CircleMarkers
        callback = """
        function (row) {
            var radius = Math.min(Math.max(row[4] / 5, 3), 15);
            var marker = L.circleMarker(new L.LatLng(row[0], row[1]), {
                radius: radius,
                color: row[3],
                fillColor: row[3],
                fillOpacity: 0.6,
                weight: 1
            });
            marker.bindPopup(row[2]);
            marker.bindTooltip(row[2].split('<br>')[0] + ': ' + row[4] + ' pers.');
            return marker;
        }
        """
        FastMarkerCluster(data=marker_data, callback=callback).add_to(m)

        # Legende categories
        categories_presentes = [
            categorie for categorie in couleurs.keys()
            if categorie in df_carte['categorie_personne'].unique()
        ]
        legend_items = "".join([
            f"<div style='margin-bottom:4px;'>"
            f"<span style='display:inline-block;width:10px;height:10px;"
            f"background:{couleurs.get(categorie, 'gray')};margin-right:6px;'></span>"
            f"{categorie}</div>"
            for categorie in categories_presentes
        ])
        if legend_items:
            legend_html = f"""
            <div style="
                position: fixed;
                bottom: 30px;
                left: 30px;
                z-index: 9999;
                background: white;
                color: black;
                padding: 10px 12px;
                border: 1px solid #ccc;
                border-radius: 6px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.2);
                font-size: 12px;
            ">
                <div style="font-weight:600;margin-bottom:6px;">Catégories</div>
                {legend_items}
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

        # Affichage de la carte
        st_folium(m, width=None, height=500, use_container_width=True)

        # Légende
        st.caption("Taille des cercles proportionnelle au nombre de personnes (par opération)")
    else:
        st.warning("Aucune donnée géographique disponible avec les filtres sélectionnés.")
else:
    st.warning("Aucune donnée disponible pour la carte.")

# =============================================================================
# Évolution temporelle
# =============================================================================
st.subheader("📈 Évolution Temporelle")

if cat_filter and cat_filter != "Toutes":
    evolution = get_kpi_evolution_categorie(categorie=cat_filter, limit=36)

    if evolution:
        df_evol = pd.DataFrame(evolution)

        fig_line = px.line(
            df_evol,
            x='periode',
            y='total_personnes',
            title=f"Évolution mensuelle - {cat_filter}",
            markers=True,
        )
        fig_line.update_layout(xaxis_title="Période", yaxis_title="Nombre de personnes")
        st.plotly_chart(fig_line, use_container_width=True)
else:
    # Évolution de toutes les catégories principales
    if comptage:
        # Prendre les 5 catégories principales (hors "Toutes catégories")
        top_categories = df_comptage[
            df_comptage['categorie_personne'] != 'Toutes catégories'
        ].groupby('categorie_personne')['total_personnes'].sum().nlargest(5).index.tolist()

        df_evol_all = df_comptage[df_comptage['categorie_personne'].isin(top_categories)]

        if not df_evol_all.empty:
            fig_area = px.area(
                df_evol_all,
                x='annee',
                y='total_personnes',
                color='categorie_personne',
                title="Évolution annuelle par catégorie (Top 5)",
            )
            st.plotly_chart(fig_area, use_container_width=True)

# =============================================================================
# Benchmark CROSS par Catégorie
# =============================================================================
st.subheader("🏆 Benchmark CROSS")

cross_data = load_cross_categorie(categorie=cat_filter)

if cross_data:
    df_cross = pd.DataFrame(cross_data)

    # Heatmap CROSS vs Catégorie
    if not df_cross.empty:
        # Regroupement Migrant/Clandestin dans le benchmark (toujours appliqué)
        if 'categorie_personne' in df_cross.columns:
            df_cross['categorie_personne'] = df_cross['categorie_personne'].replace(
                {'Clandestin': 'Migrant', 'Migrant/Clandestin': 'Migrant'}
            )
            # Exclure "Toutes catégories" pour refléter les distinctions entre catégories
            df_cross = df_cross[df_cross['categorie_personne'] != 'Toutes catégories']
            df_cross = df_cross.groupby(['cross_name', 'categorie_personne'], as_index=False).agg({
                'nb_operations': 'sum',
                'total_personnes': 'sum',
                'saines_sauves': 'sum',
                'prises_en_compte': 'sum',
                'decedes': 'sum',
                'disparus': 'sum'
            })

        # Pivot pour la heatmap
        df_pivot = df_cross.pivot_table(
            index='cross_name',
            columns='categorie_personne',
            values='total_personnes',
            aggfunc='sum',
            fill_value=0
        )

        fig_heatmap = px.imshow(
            df_pivot,
            title="Répartition des personnes: CROSS vs Catégorie",
            color_continuous_scale='YlOrRd',
            aspect='auto',
        )
        fig_heatmap.update_layout(
            xaxis_title="Catégorie de personne",
            yaxis_title="CROSS"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

# =============================================================================
# Footer
# =============================================================================
st.divider()
st.caption("""
**Sources:** Données SECMAR/SeaMIS - Ministère de la Mer

**Note méthodologique:** Le terme « Migrant » est utilisé de manière descriptive
pour désigner des personnes en situation de vulnérabilité maritime, conformément
à l'évolution terminologique post-2021 (SeaMIS).
""")

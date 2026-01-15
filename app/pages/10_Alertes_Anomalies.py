"""Page Alertes & Anomalies - Monitoring et détection d'anomalies.

Cette page affiche:
- Alertes actives (dépassement de seuils)
- Détection d'anomalies par z-score
- Historique des périodes en alerte
- Tendances et ruptures

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
    get_kpi_alertes_anomalies,
    get_kpi_alertes_actives,
    get_kpi_securite_mensuel,
)
from src.database.raw_queries import get_cross_list

# Configuration de la page
st.set_page_config(
    page_title="Alertes & Anomalies - SECMAR", page_icon="🚨", layout="wide"
)

# Authentification
if not login_required():
    st.stop()

show_user_info()

# En-tête
st.title("🚨 Alertes & Anomalies")
st.caption("Monitoring en temps réel et détection d'anomalies statistiques")

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

    cross_list = ["Tous"] + get_cross_list()
    selected_cross = st.selectbox("CROSS", options=cross_list, index=0)
    filter_cross = None if selected_cross == "Tous" else selected_cross

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
alertes_actives = get_kpi_alertes_actives(annee=annee_filter, cross=filter_cross, cross_actifs_seulement=cross_actifs_only)
alertes_historique = get_kpi_alertes_anomalies(annee=annee_filter, cross=filter_cross, cross_actifs_seulement=cross_actifs_only, limit=24)

# =============================================================================
# Statut global
# =============================================================================
st.subheader("📊 Statut Global")

if alertes_actives:
    nb_alertes = len(
        [
            a
            for a in alertes_actives
            if a.get("niveau_alerte_victimes") == "ALERTE"
            or a.get("niveau_alerte_operations") == "ALERTE"
        ]
    )
    nb_attention = len(
        [
            a
            for a in alertes_actives
            if a.get("niveau_alerte_victimes") == "ATTENTION"
            or a.get("niveau_alerte_operations") == "ATTENTION"
        ]
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if nb_alertes > 0:
            st.error(f"🔴 **{nb_alertes} ALERTE(S) CRITIQUE(S)**")
        else:
            st.success("✅ **Pas d'alerte critique**")

    with col2:
        if nb_attention > 0:
            st.warning(f"🟡 **{nb_attention} point(s) d'attention**")
        else:
            st.success("✅ **Pas de point d'attention**")

    with col3:
        st.info(f"📅 **{len(alertes_actives)} période(s) surveillée(s)**")
else:
    st.success("✅ **Tous les indicateurs sont dans les normes**")

st.divider()

# =============================================================================
# Alertes actives détaillées
# =============================================================================
st.subheader("🚨 Alertes Actives")

if alertes_actives:
    for alerte in alertes_actives[:10]:
        periode = alerte.get("periode", "N/A")
        niveau_vic = alerte.get("niveau_alerte_victimes", "NORMAL")
        niveau_ops = alerte.get("niveau_alerte_operations", "NORMAL")
        z_vic = alerte.get("zscore_victimes", 0) or 0
        z_ops = alerte.get("zscore_operations", 0) or 0
        nb_vic = alerte.get("total_victimes", 0) or 0
        nb_ops = alerte.get("nb_operations", 0) or 0
        moy_vic = alerte.get("moyenne_victimes", 0) or 0
        moy_ops = alerte.get("moyenne_operations", 0) or 0

        with st.expander(
            f"📅 {periode} - {niveau_vic if niveau_vic != 'NORMAL' else niveau_ops}",
            expanded=niveau_vic == "ALERTE" or niveau_ops == "ALERTE",
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Victimes**")
                if niveau_vic == "ALERTE":
                    st.error(f"🔴 Z-score: {z_vic:.2f} (>2.5 σ)")
                elif niveau_vic == "ATTENTION":
                    st.warning(f"🟡 Z-score: {z_vic:.2f} (>1.5 σ)")
                else:
                    st.success(f"🟢 Z-score: {z_vic:.2f} (normal)")
                st.metric("Victimes observées", nb_vic, delta=f"Moy: {moy_vic:.1f}")

            with col2:
                st.markdown("**Opérations**")
                if niveau_ops == "ALERTE":
                    st.error(f"🔴 Z-score: {z_ops:.2f} (>2.5 σ)")
                elif niveau_ops == "ATTENTION":
                    st.warning(f"🟡 Z-score: {z_ops:.2f} (>1.5 σ)")
                else:
                    st.success(f"🟢 Z-score: {z_ops:.2f} (normal)")
                st.metric("Opérations observées", nb_ops, delta=f"Moy: {moy_ops:.1f}")
else:
    st.info("Aucune alerte active pour le moment.")

st.divider()

# =============================================================================
# Graphique des anomalies
# =============================================================================
st.subheader("📈 Evolution des Z-scores")

if alertes_historique:
    df_hist = pd.DataFrame(alertes_historique)
    df_hist["periode"] = pd.to_datetime(df_hist["periode"])
    df_hist = df_hist.sort_values("periode")

    fig = go.Figure()

    # Z-score victimes
    fig.add_trace(
        go.Scatter(
            x=df_hist["periode"],
            y=df_hist["zscore_victimes"],
            mode="lines+markers",
            name="Z-score Victimes",
            line=dict(color="#e74c3c", width=2),
            marker=dict(size=8),
        )
    )

    # Z-score opérations
    fig.add_trace(
        go.Scatter(
            x=df_hist["periode"],
            y=df_hist["zscore_operations"],
            mode="lines+markers",
            name="Z-score Opérations",
            line=dict(color="#3498db", width=2),
            marker=dict(size=8),
        )
    )

    # Lignes de seuil (alignées avec les vrais seuils SQL: 1.5 et 2.5)
    fig.add_hline(
        y=2.5, line_dash="dash", line_color="red", annotation_text="Alerte (+2.5σ)"
    )
    fig.add_hline(
        y=1.5, line_dash="dot", line_color="orange", annotation_text="Attention (+1.5σ)"
    )
    fig.add_hline(y=-1.5, line_dash="dot", line_color="orange")
    fig.add_hline(
        y=-2.5, line_dash="dash", line_color="red", annotation_text="Alerte (-2.5σ)"
    )
    fig.add_hline(y=0, line_dash="solid", line_color="green", annotation_text="Moyenne")

    fig.update_layout(
        height=450,
        yaxis_title="Z-score (écarts-types)",
        xaxis_title="Période",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =============================================================================
# Historique des alertes
# =============================================================================
st.subheader("📋 Historique des périodes surveillées")

if alertes_historique:
    df_display = pd.DataFrame(alertes_historique)[
        [
            "periode",
            "nb_operations",
            "total_victimes",
            "zscore_operations",
            "zscore_victimes",
            "niveau_alerte_operations",
            "niveau_alerte_victimes",
        ]
    ].copy()

    df_display.columns = [
        "Période",
        "Opérations",
        "Victimes",
        "Z-score Ops",
        "Z-score Vic",
        "Alerte Ops",
        "Alerte Vic",
    ]

    # Formatage des z-scores
    df_display["Z-score Ops"] = df_display["Z-score Ops"].apply(
        lambda x: f"{x:.2f}" if x else "N/A"
    )
    df_display["Z-score Vic"] = df_display["Z-score Vic"].apply(
        lambda x: f"{x:.2f}" if x else "N/A"
    )

    st.dataframe(df_display, use_container_width=True, hide_index=True)

# =============================================================================
# Explication des seuils
# =============================================================================
with st.expander("ℹ️ Comment interpréter les alertes?"):
    st.markdown(
        """
    ### Système de détection d'anomalies

    Le système utilise des **Z-scores** (écarts-types) pour détecter les anomalies:

    | Niveau | Z-score | Signification |
    |--------|---------|---------------|
    | 🟢 **Normal** | -1 à +1 | Valeur dans la plage habituelle |
    | 🟡 **Attention** | +1 à +2 ou -1 à -2 | Valeur inhabituelle, à surveiller |
    | 🔴 **Alerte** | > +2 ou < -2 | Valeur significativement anormale |

    #### Formule du Z-score:
    ```
    Z = (Valeur observée - Moyenne) / Écart-type
    ```

    - Un Z-score de **+2** signifie que la valeur est **2 écarts-types au-dessus** de la moyenne
    - Statistiquement, ~95% des observations se situent entre -2 et +2
    - Une valeur au-delà de ±2 est donc considérée comme **exceptionnelle**
    """
    )

# Footer
st.divider()
st.caption("🚨 Alertes & Anomalies - Monitoring SECMAR")

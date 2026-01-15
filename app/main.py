"""Point d'entrée de l'application Streamlit - SECMAR.

Lancer avec : uv run streamlit run app/main.py
"""
import streamlit as st
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import test_connection
from src.database.base_queries import get_kpis_global
from src.auth.authentificator import login_required, show_user_info, get_current_user
from src.utils.warmload import warmload_critical_caches

# =============================================================================
# Configuration de la page
# =============================================================================
st.set_page_config(
    page_title="SECMAR - Sauvetage Maritime",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Application de gestion des opérations de sauvetage maritime SECMAR"
    }
)

# =============================================================================
# Styles CSS personnalisés
# =============================================================================
st.markdown("""
<style>
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Page principale
# =============================================================================
def main():
    """Page d'accueil de l'application."""

    # Vérifier la connexion BDD
    if not test_connection():
        st.error("❌ Impossible de se connecter à la base de données")
        st.info("""
        Vérifiez votre configuration :
        1. PostgreSQL est en cours d'exécution
        2. Le fichier `.env` contient les bons identifiants
        3. La base `secmar_db` existe

        ```bash
        # Créer la base
        sudo -u postgres createdb secmar_db

        # Exécuter le script d'initialisation
        psql -U secmar -d secmar_db -f sql/stub_tables.sql
        ```
        """)
        st.stop()

    # Authentification
    if not login_required():
        st.stop()

    # Pré-charger les caches critiques (améliore les temps de chargement)
    warmload_critical_caches()

    # Afficher infos utilisateur
    show_user_info()

    # Contenu principal
    st.title("🌊 Bienvenue sur SECMAR")
    st.markdown("""
    ### Système de Gestion des Opérations de Sauvetage Maritime

    Cette application permet de :
    - 📊 **Visualiser** les statistiques des opérations de sauvetage
    - ✏️ **Gérer** les données (opérations, flotteurs, résultats)
    - 📐 **Consulter** le schéma de la base de données
    - 📋 **Auditer** l'historique des modifications
    """)

    st.markdown("---")

    # KPIs rapides (depuis vue matérialisée - instantané)
    st.subheader("📈 Aperçu rapide")

    kpis = get_kpis_global()

    if kpis:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Opérations totales",
                value=f"{kpis.get('total_operations', 0):,}".replace(",", " ")
            )

        with col2:
            st.metric(
                label="CROSS",
                value=kpis.get('nb_cross', 0)
            )

        with col3:
            st.metric(
                label="Personnes impliquées",
                value=f"{kpis.get('total_personnes', 0):,}".replace(",", " ")
            )

        with col4:
            duree = kpis.get('duree_mediane', 0) or 0
            st.metric(
                label="Durée médiane",
                value=f"{duree:.0f} min"
            )

    st.markdown("---")

    # Accès rapide
    st.subheader("🚀 Accès rapide")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### 📊 Dashboard
        Visualisez les statistiques et tendances des opérations de sauvetage.
        """)
        st.page_link("pages/1_Dashboard.py", label="Voir le dashboard →")

    with col2:
        st.markdown("""
        #### 🔍 Opérations
        Consultez et gérez les opérations de sauvetage.
        """)
        st.page_link("pages/2_Operations.py", label="Gérer les opérations →")

    with col3:
        st.markdown("""
        #### 📋 Audit
        Consultez l'historique des modifications.
        """)
        st.page_link("pages/4_Audit.py", label="Voir l'audit →")

    # Footer
    st.markdown("---")
    st.caption("SECMAR - Approche Hybride (SQLAlchemy ORM + Raw SQL)")

    # Info utilisateur
    user = get_current_user()
    if user:
        st.caption(f"Connecté en tant que **{user['name']}** ({user['role']})")


if __name__ == "__main__":
    main()

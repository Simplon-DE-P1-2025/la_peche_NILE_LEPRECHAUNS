"""Système d'authentification Streamlit - Approche Hybride.

Ce module gère l'authentification des utilisateurs avec streamlit-authenticator.
Les utilisateurs sont stockés dans la table PostgreSQL `users`.

Usage dans une page Streamlit:
    from src.auth.authenticator import login_required, show_user_info, get_current_user

    # Au début de la page
    if not login_required():
        st.stop()

    # Afficher les infos utilisateur
    show_user_info()

    # Récupérer l'utilisateur courant
    user = get_current_user()
    if user["role"] == "admin":
        # Afficher les fonctions admin
"""

import streamlit as st
import streamlit_authenticator as stauth
import bcrypt
from typing import Optional

from src.database.connection import get_session
from src.database.crud import crud_user


# =============================================================================
# Fonctions de hash
# =============================================================================


def hash_password(password: str) -> str:
    """Hasher un mot de passe avec bcrypt.

    Args:
        password: Mot de passe en clair

    Returns:
        Hash bcrypt
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Vérifier un mot de passe.

    Args:
        password: Mot de passe en clair
        hashed: Hash bcrypt stocké

    Returns:
        True si le mot de passe correspond
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# =============================================================================
# Configuration de l'authentificateur
# =============================================================================


@st.cache_data(ttl=300)  # Cache 5 minutes pour les données utilisateurs
def get_users_config() -> dict:
    """Récupérer la configuration des utilisateurs depuis la BDD.

    Returns:
        Dictionnaire au format attendu par streamlit-authenticator
    """
    with get_session() as session:
        users = crud_user.get_active_users(session)

        config = {"credentials": {"usernames": {}}}

        for user in users:
            config["credentials"]["usernames"][user.username] = {
                "email": user.email or f"{user.username}@secmar.local",
                "name": user.username.capitalize(),
                "password": user.password_hash,
            }

        return config


def create_authenticator():
    """Créer l'authentificateur Streamlit.

    Returns:
        Instance de streamlit_authenticator.Authenticate
    """
    config = get_users_config()

    authenticator = stauth.Authenticate(
        config["credentials"],
        "secmar_cookie",  # Nom du cookie
        "secmar_signature_key",  # Clé de signature
        cookie_expiry_days=30,  # Durée du cookie
    )

    return authenticator


# =============================================================================
# Gestion des rôles
# =============================================================================


@st.cache_data(ttl=300)  # Cache 5 minutes pour les rôles
def get_user_role(username: str) -> str:
    """Récupérer le rôle d'un utilisateur.

    Args:
        username: Nom d'utilisateur

    Returns:
        Rôle (viewer, editor, admin)
    """
    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        return user.role if user else "viewer"


def has_role(required_role: str) -> bool:
    """Vérifier si l'utilisateur courant a le rôle requis.

    Args:
        required_role: Rôle minimum requis

    Returns:
        True si l'utilisateur a le rôle ou un rôle supérieur
    """
    role_hierarchy = {"viewer": 0, "editor": 1, "admin": 2}

    if "username" not in st.session_state:
        return False

    user_role = st.session_state.get("role", "viewer")
    return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)


def require_role(required_role: str) -> bool:
    """Vérifier le rôle et afficher un message si insuffisant.

    Args:
        required_role: Rôle minimum requis

    Returns:
        True si l'utilisateur a le rôle
    """
    if not has_role(required_role):
        st.error(f"Accès refusé. Rôle requis: {required_role}")
        return False
    return True


# =============================================================================
# Page de connexion
# =============================================================================


def login_page() -> Optional[bool]:
    """Afficher la page de connexion.

    Returns:
        True si connecté, False si échec, None si en attente
    """
    st.title("SECMAR - Connexion")

    authenticator = create_authenticator()

    try:
        authenticator.login(location="main")
    except Exception as e:
        # Effacer la session corrompue pour permettre une nouvelle connexion
        for key in ["authentication_status", "username", "name", "authenticated", "role"]:
            if key in st.session_state:
                del st.session_state[key]
        st.warning("Session expirée ou invalide. Veuillez vous reconnecter.")
        st.rerun()
        return None

    # Récupérer les valeurs depuis session_state (nouvelle API)
    authentication_status = st.session_state.get("authentication_status")
    name = st.session_state.get("name")
    username = st.session_state.get("username")

    if authentication_status:
        # Stocker les infos en session
        st.session_state["role"] = get_user_role(username)
        st.session_state["authenticated"] = True

        st.success(f"Bienvenue {name}!")
        return True

    elif authentication_status is False:
        st.error("Nom d'utilisateur ou mot de passe incorrect")
        return False

    # En attente de saisie
    return None


def login_required() -> bool:
    """Vérifier si l'utilisateur est connecté, sinon afficher login.

    Usage:
        if not login_required():
            st.stop()

    Returns:
        True si connecté
    """
    if st.session_state.get("authenticated"):
        return True

    result = login_page()
    return result is True


# =============================================================================
# Déconnexion
# =============================================================================


def logout():
    """Déconnecter l'utilisateur et réinitialiser la session."""
    # Créer l'authenticator pour accéder à la gestion du cookie
    authenticator = create_authenticator()

    # Utiliser la méthode native qui supprime le cookie
    # location='unrendered' exécute la logique sans afficher de bouton
    authenticator.logout(location='unrendered')

    # Nettoyer les clés de session personnalisées
    keys_to_clear = [
        "role",
        "authenticated",
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


# =============================================================================
# Informations utilisateur
# =============================================================================


def get_current_user() -> Optional[dict]:
    """Récupérer les informations de l'utilisateur courant.

    Returns:
        Dictionnaire {username, name, role} ou None
    """
    if not st.session_state.get("authenticated"):
        return None

    return {
        "username": st.session_state.get("username"),
        "name": st.session_state.get("name"),
        "role": st.session_state.get("role", "viewer"),
    }


def show_user_info():
    """Afficher les informations utilisateur dans la sidebar."""
    user = get_current_user()

    if user:
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"**{user['name']}**")

            # Badge de rôle avec couleur
            role_colors = {"admin": "red", "editor": "orange", "viewer": "green"}
            role = user["role"]
            color = role_colors.get(role, "gray")

            st.markdown(
                f'<span style="background-color:{color};'
                f"padding:2px 8px;border-radius:4px;color:white;"
                f'font-size:12px">{role.upper()}</span>',
                unsafe_allow_html=True,
            )

            st.caption(f"@{user['username']}")

            if st.button("Deconnexion", use_container_width=True):
                logout()


def show_login_status():
    """Afficher le statut de connexion en haut de page."""
    user = get_current_user()

    if user:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col2:
            st.caption(f"{user['name']} ({user['role']})")
        with col3:
            if st.button("Logout", key="top_logout"):
                logout()


# =============================================================================
# Décorateur pour les fonctions protégées
# =============================================================================


def protected(role: str = "viewer"):
    """Décorateur pour protéger une fonction par rôle.

    Usage:
        @protected("editor")
        def edit_operation():
            ...

    Args:
        role: Rôle minimum requis
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not st.session_state.get("authenticated"):
                st.error("Veuillez vous connecter")
                return None

            if not has_role(role):
                st.error(f"Accès refusé. Rôle requis: {role}")
                return None

            return func(*args, **kwargs)

        return wrapper

    return decorator

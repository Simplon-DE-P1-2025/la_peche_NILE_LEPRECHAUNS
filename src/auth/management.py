"""Gestion des utilisateurs (admin).

Ce module fournit les fonctions d'administration des utilisateurs :
- Création d'utilisateurs
- Modification des rôles
- Activation/désactivation
- Liste des utilisateurs

Usage:
    from src.auth.management import create_user, list_users, update_user_role

    # Créer un utilisateur
    success = create_user("john", "password123", "john@email.com", "editor")

    # Lister les utilisateurs
    users = list_users()

    # Changer le rôle
    update_user_role("john", "admin")
"""

from typing import Optional
from datetime import datetime

from src.database.connection import get_session
from src.database.crud import crud_user
from src.auth.authentificator import hash_password


def create_user(
    username: str, password: str, email: str = None, role: str = "viewer"
) -> bool:
    """Créer un nouvel utilisateur.

    Args:
        username: Nom d'utilisateur (unique)
        password: Mot de passe en clair (sera hashé)
        email: Email optionnel
        role: Rôle (viewer, editor, admin)

    Returns:
        True si créé, False si username existe déjà
    """
    with get_session() as session:
        # Vérifier si l'utilisateur existe
        existing = crud_user.get_by_username(session, username)
        if existing:
            return False

        user_data = {
            "username": username,
            "password_hash": hash_password(password),
            "email": email,
            "role": role,
            "is_active": True,
        }

        crud_user.create(session, user_data, user="admin")
        return True


def update_user_role(username: str, new_role: str) -> bool:
    """Modifier le rôle d'un utilisateur.

    Args:
        username: Nom d'utilisateur
        new_role: Nouveau rôle (viewer, editor, admin)

    Returns:
        True si modifié, False si utilisateur non trouvé
    """
    if new_role not in ("viewer", "editor", "admin"):
        return False

    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        if not user:
            return False

        crud_user.update(session, user, {"role": new_role}, user="admin")
        return True


def update_user_password(username: str, new_password: str) -> bool:
    """Modifier le mot de passe d'un utilisateur.

    Args:
        username: Nom d'utilisateur
        new_password: Nouveau mot de passe (sera hashé)

    Returns:
        True si modifié, False si utilisateur non trouvé
    """
    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        if not user:
            return False

        crud_user.update(
            session, user, {"password_hash": hash_password(new_password)}, user="admin"
        )
        return True


def deactivate_user(username: str) -> bool:
    """Désactiver un utilisateur (soft delete).

    Args:
        username: Nom d'utilisateur

    Returns:
        True si désactivé, False si non trouvé
    """
    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        if not user:
            return False

        crud_user.update(session, user, {"is_active": False}, user="admin")
        return True


def activate_user(username: str) -> bool:
    """Réactiver un utilisateur.

    Args:
        username: Nom d'utilisateur

    Returns:
        True si activé, False si non trouvé
    """
    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        if not user:
            return False

        crud_user.update(session, user, {"is_active": True}, user="admin")
        return True


def delete_user(username: str) -> bool:
    """Supprimer définitivement un utilisateur.

    Args:
        username: Nom d'utilisateur

    Returns:
        True si supprimé, False si non trouvé
    """
    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        if not user:
            return False

        session.delete(user)
        return True


def list_users(include_inactive: bool = False) -> list[dict]:
    """Lister tous les utilisateurs.

    Args:
        include_inactive: Inclure les utilisateurs désactivés

    Returns:
        Liste de dictionnaires avec les infos utilisateur
    """
    with get_session() as session:
        if include_inactive:
            users = crud_user.get_multi(session, limit=1000)
        else:
            users = crud_user.get_active_users(session)

        return [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "last_login": u.last_login,
                "created_at": u.created_at,
            }
            for u in users
        ]


def get_user_details(username: str) -> Optional[dict]:
    """Récupérer les détails d'un utilisateur.

    Args:
        username: Nom d'utilisateur

    Returns:
        Dictionnaire avec les détails ou None
    """
    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        if not user:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }


def update_last_login(username: str) -> None:
    """Mettre à jour la date de dernière connexion.

    Args:
        username: Nom d'utilisateur
    """
    with get_session() as session:
        user = crud_user.get_by_username(session, username)
        if user:
            crud_user.update(
                session, user, {"last_login": datetime.utcnow()}, user="system"
            )


def count_users_by_role() -> dict[str, int]:
    """Compter les utilisateurs par rôle.

    Returns:
        Dictionnaire {role: count}
    """
    users = list_users(include_inactive=False)

    counts = {"viewer": 0, "editor": 0, "admin": 0}
    for user in users:
        role = user["role"]
        if role in counts:
            counts[role] += 1

    return counts


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Valider la force d'un mot de passe.

    Args:
        password: Mot de passe à valider

    Returns:
        Tuple (is_valid, message)
    """
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"

    if not any(c.isupper() for c in password):
        return False, "Le mot de passe doit contenir au moins une majuscule"

    if not any(c.islower() for c in password):
        return False, "Le mot de passe doit contenir au moins une minuscule"

    if not any(c.isdigit() for c in password):
        return False, "Le mot de passe doit contenir au moins un chiffre"

    return True, "Mot de passe valide"

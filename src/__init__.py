"""Package auth - Authentification Streamlit."""

"""from src.auth.authenticator import (
    login_required,
    login_page,
    logout,
    get_current_user,
    show_user_info,
    has_role,
    require_role,
    protected,
)
from src.auth.management import (
    create_user,
    list_users,
    update_user_role,
    update_user_password,
    deactivate_user,
    activate_user,
)"""

__all__ = [
    # Authenticator
    "login_required",
    "login_page",
    "logout",
    "get_current_user",
    "show_user_info",
    "has_role",
    "require_role",
    "protected",
    # Management
    "create_user",
    "list_users",
    "update_user_role",
    "update_user_password",
    "deactivate_user",
    "activate_user",
]

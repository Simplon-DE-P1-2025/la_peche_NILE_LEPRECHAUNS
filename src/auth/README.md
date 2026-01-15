# src/auth/ - Authentification

> Systeme d'authentification et de gestion des roles pour l'application Streamlit.

## But

Ce module gere l'authentification des utilisateurs avec streamlit-authenticator et le stockage des utilisateurs en base de donnees PostgreSQL.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `authentificator.py` | Authentification Streamlit, hash bcrypt, verification des roles |
| `management.py` | Gestion des utilisateurs (CRUD) |

## Roles disponibles

| Role | Droits |
|------|--------|
| `viewer` | Lecture seule |
| `editor` | Lecture et modification |
| `admin` | Acces complet (gestion utilisateurs incluse) |

## Utilisation

```python
from src.auth.authentificator import login_required, get_current_user

# Proteger une page
if not login_required():
    st.stop()

# Recuperer l'utilisateur courant
user = get_current_user()
if user["role"] == "admin":
    # Afficher les fonctions admin
    pass
```

## Fonctions principales

| Fonction | Description |
|----------|-------------|
| `login_required()` | Affiche le formulaire de connexion, retourne True si connecte |
| `get_current_user()` | Retourne les infos de l'utilisateur connecte |
| `show_user_info()` | Affiche les infos utilisateur dans la sidebar |
| `hash_password()` | Hashe un mot de passe avec bcrypt |
| `verify_password()` | Verifie un mot de passe |

## Dependances

- streamlit-authenticator
- bcrypt

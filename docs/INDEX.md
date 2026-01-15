# SECMAR - Index de Documentation

> Table des matieres et guide de navigation pour le projet SECMAR

## Vue d'ensemble

Ce projet est une application de gestion des operations de sauvetage maritime (SECMAR) avec :
- Interface web Streamlit pour la visualisation et la gestion des donnees
- Pipeline ETL pour l'importation depuis data.gouv.fr
- Base de donnees PostgreSQL avec ORM SQLAlchemy
- Systeme d'authentification par roles

---

## Structure du projet

```
la_peche_NILE_LEPRECHAUNS/
├── app/                    # Application Streamlit
├── src/                    # Code metier
│   ├── database/           # Couche de donnees
│   ├── auth/               # Authentification
│   ├── schema/             # Generation de formulaires
│   ├── validation/         # Validation des donnees
│   ├── etl/                # Pipeline ETL
│   └── analytics/          # Requetes analytiques
├── sql/                    # Scripts SQL
├── config/                 # Configuration YAML
├── data/                   # Donnees locales
├── docs/                   # Documentation
└── test/                   # Tests
```

---

## Documentation par module

### Application (`app/`)

| Document | Description |
|----------|-------------|
| [app/README.md](../app/README.md) | Documentation de l'application Streamlit |
| [app/components/README.md](../app/components/README.md) | Composants UI reutilisables |

### Code metier (`src/`)

| Document | Description |
|----------|-------------|
| [src/README.md](../src/README.md) | Vue d'ensemble du code metier |
| [src/database/README.md](../src/database/README.md) | Modeles ORM, CRUD, connexion PostgreSQL |
| [src/auth/README.md](../src/auth/README.md) | Authentification et gestion des roles |
| [src/schema/README.md](../src/schema/README.md) | Generation automatique de formulaires |
| [src/validation/README.md](../src/validation/README.md) | Validation des donnees (Pandera) |
| [src/etl/README.md](../src/etl/README.md) | Pipeline ETL |
| [src/analytics/README.md](../src/analytics/README.md) | Requetes analytiques |

### Infrastructure

| Document | Description |
|----------|-------------|
| [sql/README.md](../sql/README.md) | Scripts SQL et vues KPI |
| [config/README.md](../config/README.md) | Configuration YAML |

### Documentation metier

| Document | Description |
|----------|-------------|
| [KPI_DOCUMENTATION.md](KPI_DOCUMENTATION.md) | Documentation complete des KPIs |

---

## Demarrage rapide

### Prerequis

- Python 3.10+
- PostgreSQL 14+
- uv (gestionnaire de paquets)

### Installation

```bash
# Installer uv
pip install uv

# Installer les dependances
uv sync

# Configurer les variables d'environnement
cp .env.example .env
# Editer .env avec vos parametres PostgreSQL
```

### Lancement

```bash
# Lancer l'application Streamlit
uv run streamlit run app/main.py

# Lancer le pipeline ETL
uv run python src/main.py
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│  APP (Streamlit)                        │  Interface utilisateur
│  10 pages + composants reutilisables    │
├─────────────────────────────────────────┤
│  SRC (Logique Metier)                   │
│  ├─ Schema (Formulaires)                │
│  ├─ Auth (Authentification)             │
│  ├─ Validation (Pandera)                │
│  ├─ Analytics (Requetes)                │
│  └─ ETL (Pipelines)                     │
├─────────────────────────────────────────┤
│  DATABASE (PostgreSQL + SQLAlchemy)     │  Persistance
└─────────────────────────────────────────┘
```

---

## Entites principales

| Entite | Description |
|--------|-------------|
| **Operation** | Operation de sauvetage maritime |
| **Flotteur** | Navire/flotteur implique dans une operation |
| **ResultatHumain** | Personne secourue/impliquee |
| **User** | Utilisateur de l'application |
| **AuditLog** | Journal des modifications |

---

## Roles utilisateurs

| Role | Droits |
|------|--------|
| `viewer` | Lecture seule |
| `editor` | Lecture et modification |
| `admin` | Acces complet |

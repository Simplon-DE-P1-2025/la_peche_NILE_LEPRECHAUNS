# SECMAR - Gestion des Operations de Sauvetage Maritime

> Application de gestion et d'analyse des operations de sauvetage maritime coordonnees par les CROSS (Centres Regionaux Operationnels de Surveillance et de Sauvetage).

## Fonctionnalites

- **Dashboard analytique** : Visualisation des operations par CROSS, type, periode
- **Gestion CRUD** : Operations, flotteurs, resultats humains
- **KPIs officiels** : Indicateurs alignes sur le Programme 205 (Budget.gouv.fr)
- **Pipeline ETL** : Import automatique depuis data.gouv.fr
- **Audit complet** : Tracabilite des modifications
- **Authentification** : Gestion par roles (viewer, editor, admin)

## Prerequis

- Python 3.10+
- PostgreSQL 14+
- uv (gestionnaire de paquets Python)

## Installation

```bash
# Installer uv
pip install uv

# Installer les dependances
uv sync

# Configurer l'environnement
cp .env.example .env
# Editer .env avec vos parametres de connexion PostgreSQL
```

## Lancement

```bash
# Application Streamlit
uv run streamlit run app/main.py

# Pipeline ETL
uv run python src/main.py
```

## Documentation

Voir [docs/INDEX.md](docs/INDEX.md) pour la documentation complete.

| Module | Description |
|--------|-------------|
| [app/](app/README.md) | Application Streamlit |
| [src/](src/README.md) | Code metier |
| [sql/](sql/README.md) | Scripts SQL |
| [config/](config/README.md) | Configuration |

## Structure

```
├── app/                # Application Streamlit (11 pages)
├── src/                # Code metier
│   ├── database/       # ORM SQLAlchemy, CRUD
│   ├── auth/           # Authentification
│   ├── schema/         # Generation de formulaires
│   ├── validation/     # Validation Pandera
│   ├── etl/            # Pipeline ETL
│   ├── analytics/      # Requetes analytiques
│   └── utils/          # Utilitaires (performance, filtres)
├── sql/                # Scripts SQL
├── config/             # Configuration YAML
├── data/               # Donnees (raw/processed)
└── docs/               # Documentation
```

## Source des donnees

Donnees ouvertes : [Operations coordonnees par les CROSS](https://www.data.gouv.fr/fr/datasets/operations-coordonnees-par-les-cross/) (data.gouv.fr)

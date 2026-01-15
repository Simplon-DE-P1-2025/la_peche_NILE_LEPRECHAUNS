# src/ - Code Metier

> Logique metier et services backend de l'application SECMAR.

## But

Ce module contient toute la logique metier separee de l'interface utilisateur : acces aux donnees, authentification, validation, pipeline ETL et requetes analytiques.

## Modules

| Module | Description |
|--------|-------------|
| [database/](database/README.md) | Modeles ORM, CRUD, connexion PostgreSQL |
| [auth/](auth/README.md) | Authentification et gestion des roles |
| [schema/](schema/README.md) | Generation automatique de formulaires |
| [validation/](validation/README.md) | Validation des donnees (Pandera) |
| [etl/](etl/README.md) | Pipeline ETL (Extract, Transform, Load) |
| [analytics/](analytics/README.md) | Requetes analytiques pour les dashboards |

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `main.py` | Point d'entree du pipeline ETL |
| `config.py` | Configuration generale |

## Architecture

```
src/
├── main.py              # Pipeline ETL
├── config.py            # Configuration
├── database/            # Couche de donnees
├── auth/                # Authentification
├── schema/              # Formulaires
├── validation/          # Validation
├── etl/                 # Pipeline
└── analytics/           # Requetes
```

## Dependances principales

- SQLAlchemy (ORM)
- Pandera (validation)
- bcrypt (authentification)
- pandas (manipulation de donnees)

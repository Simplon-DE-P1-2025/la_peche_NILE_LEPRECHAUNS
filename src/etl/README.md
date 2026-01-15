# src/etl/ - Pipeline ETL

> Pipeline d'extraction, transformation et chargement des donnees SECMAR.

## But

Ce module automatise l'importation des donnees depuis data.gouv.fr vers la base PostgreSQL. Il extrait les CSV, les valide, les transforme et les charge en base.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `extract.py` | Extraction des CSV depuis data.gouv.fr |
| `transform.py` | Transformation et nettoyage des donnees |
| `load.py` | Chargement en base PostgreSQL |
| `pipelines.py` | Orchestration du pipeline complet |

## Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EXTRACT   │ -> │   VALIDATE  │ -> │  TRANSFORM  │ -> │    LOAD     │
│ data.gouv.fr│    │   Pandera   │    │   Pandas    │    │  PostgreSQL │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Utilisation

```bash
# Lancer le pipeline complet
uv run python src/main.py
```

```python
from src.etl.pipelines import pipeline_db_raw

# Executer le pipeline
pipeline_db_raw()
```

## Configuration

Le pipeline utilise `config/config_clean.yml` pour :
- URL du dataset data.gouv.fr
- Timeout de telechargement
- Dossier de sortie des CSV
- Schemas de validation

## Fichiers de donnees

| Fichier | Description |
|---------|-------------|
| `operations.csv` | Operations de sauvetage |
| `flotteurs.csv` | Flotteurs impliques |
| `resultats_humain.csv` | Resultats humains |

## Dependances

- requests (telechargement)
- pandas (manipulation)
- Pandera (validation)
- SQLAlchemy (chargement)

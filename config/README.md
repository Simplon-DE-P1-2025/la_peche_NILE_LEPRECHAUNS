# config/ - Configuration

> Fichiers de configuration YAML pour l'application.

## But

Ce dossier centralise la configuration de l'application : sources de donnees, parametres de validation, et options diverses.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `config_clean.yml` | Configuration principale (source de verite) |
| `config.yml` | Configuration alternative/archive |

## Structure de config_clean.yml

```yaml
EXTRACT:
  dataset_url: "https://www.data.gouv.fr/api/..."
  timeout_sec: 20
  output_dir: "data/raw"

DATA_VALIDATION:
  flotteurs:
    operation_id:
      type: int
      nullable: false
    # ...
  operations:
    # ...
  resultats_humain:
    # ...
```

## Sections

### EXTRACT

Configuration du pipeline d'extraction :

| Parametre | Description |
|-----------|-------------|
| `dataset_url` | URL de l'API data.gouv.fr |
| `timeout_sec` | Timeout de telechargement |
| `output_dir` | Dossier de sortie des CSV |

### DATA_VALIDATION

Schemas de validation Pandera pour chaque entite :
- Types de donnees
- Contraintes nullable
- Regles de validation (checks)

## Utilisation

```python
from src.etl.extract import load_config

config = load_config("config/config_clean.yml")

# Acces aux parametres
url = config["EXTRACT"]["dataset_url"]
validation_rules = config["DATA_VALIDATION"]["operations"]
```

## Variables d'environnement

Les parametres sensibles (connexion BDD) sont dans `.env` :

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=secmar
POSTGRES_USER=postgres
POSTGRES_PASSWORD=xxxxx
```

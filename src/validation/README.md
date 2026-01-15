# src/validation/ - Validation des Donnees

> Framework de validation des donnees avec Pandera et validateurs metier.

## But

Ce module assure la qualite des donnees a l'entree du systeme (pipeline ETL) et lors des modifications (formulaires). Il utilise Pandera pour la validation de schemas et des validateurs metier personnalises.

## Fichiers principaux

| Fichier | Description |
|---------|-------------|
| `base.py` | Classes de base pour les validateurs |
| `validators.py` | Validateurs metier (regles SECMAR) |
| `schema_validation.py` | Construction de schemas Pandera depuis la config YAML |
| `integration.py` | Validation d'integration (coherence entre tables) |

## Sous-dossier schemas/

| Fichier | Description |
|---------|-------------|
| `schemas/operation.py` | Schema de validation Operation |
| `schemas/flotteur.py` | Schema de validation Flotteur |
| `schemas/resultat_humain.py` | Schema de validation ResultatHumain |

## Utilisation

```python
from src.validation.schema_validation import build_dataframe_schema, valider_csv

# Construire un schema depuis la config
schema = build_dataframe_schema(config["DATA_VALIDATION"]["operations"])

# Valider un DataFrame
df_valide = valider_csv(df, schema)
```

## Types de validation

| Type | Description |
|------|-------------|
| **Schema** | Types de donnees, nullable, contraintes (Pandera) |
| **Metier** | Regles SECMAR (coherence dates, valeurs autorisees) |
| **Integration** | Coherence entre tables (FK, relations) |

## Dependances

- Pandera
- pandas

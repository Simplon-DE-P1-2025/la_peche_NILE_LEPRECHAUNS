# Tests Unitaires - la_peche_NILE_LEPRECHAUNS

Ce répertoire contient tous les tests unitaires pour le projet.

## Structure des tests

```
test/
├── __init__.py              # Initialisation du package de tests
├── README.md                # Ce fichier
│
├── # Tests ETL
├── test_extract.py          # Tests pour src/etl/extract.py (load_config)
├── test_transform.py        # Tests pour src/etl/transform.py
├── test_load.py             # Tests pour src/etl/load.py (load_df_to_db)
├── test_pipelines.py        # Tests pour src/etl/pipelines.py (pipeline_db_raw, pipeline_db_cleaned)
│
├── # Tests Validation
├── test_validators.py       # Tests pour src/validation/validators.py (checks Pandera)
├── test_schema_validation.py # Tests pour src/validation/schema_validation.py
├── test_base.py             # Tests pour src/validation/base.py (ValidationMode, ValidationResult)
├── test_integration.py      # Tests pour src/validation/integration.py (SchemaConverter)
│
└── # Exemples
    └── test_utils.py        # Tests d'exemple pour apprendre (src/utils.py)
```

## Modules testés

### ETL (src/etl/)
| Fichier de test | Module testé | Fonctions testées |
|-----------------|--------------|-------------------|
| `test_extract.py` | `extract.py` | `load_config()` |
| `test_load.py` | `load.py` | `load_df_to_db()` |
| `test_pipelines.py` | `pipelines.py` | `pipeline_db_raw()`, `pipeline_db_cleaned()` |
| `test_transform.py` | `transform.py` | (à compléter) |

### Validation (src/validation/)
| Fichier de test | Module testé | Fonctions/Classes testées |
|-----------------|--------------|---------------------------|
| `test_validators.py` | `validators.py` | `coordinates_check()`, `coordinates_in_france()`, `beaufort_scale_check()`, `douglas_scale_check()`, `departement_format_check()`, `resultat_humain_coherence()`, `flotteur_longueur_type_coherence()` |
| `test_schema_validation.py` | `schema_validation.py` | `build_dataframe_schema()`, `valider_csv()` |
| `test_base.py` | `base.py` | `ValidationMode`, `ValidationResult`, `EnumWarningCollector`, `create_enum_column()` |
| `test_integration.py` | `integration.py` | `SchemaConverter`, `validate_for_crud()`, `validate_dataframe()` |

## Installation des dépendances

```bash
# Avec uv (recommandé)
uv sync

# Ou avec pip
pip install -e .
```

## Exécution des tests

### Tous les tests
```bash
pytest
```

### Par module

```bash
# Tests ETL
pytest test/test_extract.py test/test_load.py test/test_pipelines.py -v

# Tests Validation
pytest test/test_validators.py test/test_schema_validation.py test/test_base.py test/test_integration.py -v
```

### Un fichier spécifique
```bash
pytest test/test_validators.py -v
```

### Une classe spécifique
```bash
pytest test/test_validators.py::TestBeaufortScaleCheck -v
```

### Un test spécifique
```bash
pytest test/test_validators.py::TestBeaufortScaleCheck::test_valeur_valide_minimum -v
```

### Options utiles
```bash
pytest -v              # Verbeux
pytest -s              # Afficher les print()
pytest -x              # S'arrêter au premier échec
pytest --lf            # Relancer les tests échoués
pytest --cov=src       # Couverture de code (nécessite pytest-cov)
```

## Couverture de code

Pour générer un rapport de couverture (nécessite `pytest-cov`):

```bash
# Installer pytest-cov si nécessaire
pip install pytest-cov

# Lancer avec couverture
pytest --cov=src --cov-report=html

# Ouvrir le rapport
open htmlcov/index.html  # macOS
```

## Résumé des tests par fichier

### test_validators.py (30 tests)
- `TestCoordinatesCheck` - 4 tests
- `TestCoordinatesInFrance` - 4 tests
- `TestBeaufortScaleCheck` - 6 tests
- `TestDouglasScaleCheck` - 4 tests
- `TestDepartementFormatCheck` - 6 tests
- `TestResultatHumainCoherence` - 3 tests
- `TestFlotteurLongueurTypeCoherence` - 3 tests

### test_schema_validation.py (12 tests)
- `TestBuildDataframeSchema` - 6 tests
- `TestValiderCsv` - 2 tests
- `TestTypeValidation` - 4 tests

### test_base.py (18 tests)
- `TestValidationMode` - 2 tests
- `TestValidationResult` - 3 tests
- `TestEnumWarningCollector` - 6 tests
- `TestCreateEnumCheckWarning` - 2 tests
- `TestCreateEnumColumn` - 5 tests

### test_integration.py (17 tests)
- `TestWidgetToPanderaMapping` - 4 tests
- `TestSchemaConverter` - 6 tests
- `TestValidateForCrud` - 3 tests
- `TestValidateDataframe` - 2 tests
- `TestValidationResultIntegration` - 2 tests

### test_extract.py (2 tests)
- `TestLoadConfig` - 2 tests

### test_load.py (3 tests)
- `TestLoadDfToDb` - 3 tests

### test_pipelines.py (3 tests)
- `TestPipelineDbRaw` - 2 tests
- `TestPipelineDbCleaned` - 1 test

### test_utils.py (3 tests)
- Tests d'exemple pour apprendre

## Bonnes pratiques

1. **Structure AAA** : Arrange, Act, Assert
2. **Un test = une chose** : Chaque test vérifie un seul comportement
3. **Noms descriptifs** : `test_validation_echoue_si_champ_requis_vide`
4. **Isolation** : Les tests ne dépendent pas les uns des autres
5. **Mocks** : Simuler les dépendances externes (DB, API, fichiers)

## Exemple de test simple

```python
def test_addition():
    # ARRANGE (Préparer)
    a = 5
    b = 3

    # ACT (Agir)
    resultat = a + b

    # ASSERT (Vérifier)
    assert resultat == 8
```

## Exemple avec mock

```python
from unittest.mock import patch, MagicMock

@patch('src.module.fonction_externe')
def test_avec_mock(mock_fonction):
    # Configurer le mock
    mock_fonction.return_value = "valeur simulée"

    # Appeler la fonction à tester
    resultat = ma_fonction()

    # Vérifier
    mock_fonction.assert_called_once()
    assert resultat == "valeur attendue"
```

## Dépannage

### ImportError
```bash
pip install -e .
```

### Tests non découverts
Vérifier que:
- Fichiers commencent par `test_`
- Classes commencent par `Test`
- Fonctions commencent par `test_`
- `__init__.py` existe dans `test/`

### Erreur pytest-cov
```bash
# Lancer sans couverture
pytest --override-ini="addopts="
```

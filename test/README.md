# Tests Unitaires - la_peche_NILE_LEPRECHAUNS

Ce répertoire contient tous les tests unitaires pour le projet.

## Structure des tests

```
test/
├── __init__.py           # Initialisation du package de tests
├── test_extract.py       # Tests pour les fonctions d'extraction (src/etl/extract.py)
├── test_transform.py     # Tests pour les fonctions de transformation (src/etl/transform.py)
├── test_load.py          # Tests pour les fonctions de chargement (src/etl/load.py)
└── README.md            # Ce fichier
```

## Installation des dépendances de test

Les dépendances de test sont déjà incluses dans le `pyproject.toml`. Pour les installer:

```bash
uv sync
```

ou si vous utilisez pip:

```bash
pip install -e .
```

## Exécution des tests

### Exécuter tous les tests
```bash
pytest
```

### Exécuter un fichier de test spécifique
```bash
pytest test/test_extract.py
pytest test/test_load.py
pytest test/test_transform.py
```

### Exécuter une classe de test spécifique
```bash
pytest test/test_extract.py::TestLoadConfig
pytest test/test_load.py::TestLoadDfToDb
```

### Exécuter un test spécifique
```bash
pytest test/test_extract.py::TestLoadConfig::test_load_config_success
```

### Exécuter avec verbosité
```bash
pytest -v
```

### Exécuter avec rapport de couverture
```bash
pytest --cov=src --cov-report=html
```

Le rapport HTML sera généré dans `htmlcov/index.html`

### Exécuter avec capture de sortie désactivée (pour voir les prints)
```bash
pytest -s
```

### Exécuter uniquement les tests qui ont échoué la dernière fois
```bash
pytest --lf
```

### Exécuter en mode parallèle (plus rapide)
```bash
pytest -n auto
```
Note: nécessite `pytest-xdist` (à ajouter si besoin)

## Markers personnalisés

Les tests peuvent être marqués avec des markers personnalisés:

- `@pytest.mark.slow` - Tests lents
- `@pytest.mark.integration` - Tests d'intégration
- `@pytest.mark.unit` - Tests unitaires

### Exécuter uniquement certains types de tests
```bash
# Exécuter seulement les tests unitaires
pytest -m unit

# Exclure les tests lents
pytest -m "not slow"

# Exécuter les tests d'intégration
pytest -m integration
```

## Couverture de code

La configuration pytest est définie pour générer automatiquement des rapports de couverture:

- **Terminal**: Affiche le pourcentage de couverture après chaque exécution
- **HTML**: Génère un rapport détaillé dans `htmlcov/`

### Visualiser le rapport de couverture HTML
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html  # Sur macOS
```

## Bonnes pratiques

1. **Nommage**: Les fichiers de test doivent commencer par `test_`
2. **Organisation**: Une classe de test par fonction ou groupe de fonctions liées
3. **Isolation**: Chaque test doit être indépendant des autres
4. **Fixtures**: Utilisez des fixtures pytest pour le code de setup réutilisable
5. **Mocking**: Utilisez `unittest.mock` pour simuler les dépendances externes
6. **Assertions**: Utilisez des assertions claires et descriptives

## Exemples de tests

### Test avec fixture
```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_example(sample_data):
    assert sample_data["key"] == "value"
```

### Test avec mock
```python
from unittest.mock import patch, MagicMock

@patch('module.function')
def test_with_mock(mock_function):
    mock_function.return_value = "mocked"
    result = my_function()
    assert result == "expected"
```

### Test avec exception
```python
def test_exception():
    with pytest.raises(ValueError) as exc_info:
        raise_error()
    assert "error message" in str(exc_info.value)
```

## Dépannage

### Les imports ne fonctionnent pas
Assurez-vous d'être dans le répertoire racine du projet et que le package est installé:
```bash
pip install -e .
```

### Les tests ne sont pas découverts
Vérifiez que:
- Les fichiers commencent par `test_`
- Les classes commencent par `Test`
- Les fonctions commencent par `test_`
- Le fichier `__init__.py` existe dans le dossier `test/`

### Erreurs de dépendances
Réinstallez les dépendances:
```bash
uv sync
# ou
pip install -e .
```

## Ajout de nouveaux tests

Pour ajouter des tests pour un nouveau module:

1. Créer un fichier `test_<nom_module>.py` dans ce dossier
2. Importer le module à tester
3. Créer des classes de test avec le préfixe `Test`
4. Écrire des fonctions de test avec le préfixe `test_`
5. Utiliser des assertions pour vérifier le comportement attendu

Exemple:
```python
"""Tests pour mon_module"""
import pytest
from src.mon_module import ma_fonction

class TestMaFonction:
    """Tests pour ma_fonction"""

    def test_cas_nominal(self):
        """Test du cas nominal"""
        result = ma_fonction(input_data)
        assert result == expected_output

    def test_cas_erreur(self):
        """Test du cas d'erreur"""
        with pytest.raises(ValueError):
            ma_fonction(invalid_input)
```

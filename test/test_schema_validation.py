"""
Tests unitaires pour la validation de schémas (src/validation/schema_validation.py)

Ces fonctions construisent des schémas Pandera et valident des fichiers CSV.
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from pandera import DataFrameSchema
from src.validation.schema_validation import build_dataframe_schema, valider_csv


# =============================================================================
#                Tests pour build_dataframe_schema()
# =============================================================================

class TestBuildDataframeSchema:
    """Tests pour la construction de schémas Pandera"""

    def test_schema_simple_avec_types(self):
        """
        Test 1: Créer un schéma avec différents types de colonnes
        """
        # ARRANGE - Définition du schéma
        schema_dict = {
            'id': {'type': 'int', 'nullable': False},
            'nom': {'type': 'str', 'nullable': True},
            'prix': {'type': 'float', 'nullable': True}
        }

        # ACT
        schema = build_dataframe_schema(schema_dict)

        # ASSERT
        assert isinstance(schema, DataFrameSchema)
        assert 'id' in schema.columns
        assert 'nom' in schema.columns
        assert 'prix' in schema.columns

    def test_schema_avec_check_greater_than(self):
        """
        Test 2: Schéma avec une contrainte "greater_than"
        """
        # ARRANGE
        schema_dict = {
            'age': {
                'type': 'int',
                'nullable': True,
                'checks': [{'greater_than': 0}]
            }
        }

        # ACT
        schema = build_dataframe_schema(schema_dict)

        # ASSERT - Vérifions que le schéma valide correctement
        df_valide = pd.DataFrame({'age': [25, 30]})
        resultat = schema.validate(df_valide)
        assert len(resultat) == 2

    def test_schema_avec_check_less_than(self):
        """
        Test 3: Schéma avec une contrainte "less_than"
        """
        # ARRANGE
        schema_dict = {
            'score': {
                'type': 'int',
                'nullable': True,
                'checks': [{'less_than': 100}]
            }
        }

        # ACT
        schema = build_dataframe_schema(schema_dict)

        # ASSERT
        df_valide = pd.DataFrame({'score': [50, 99]})
        resultat = schema.validate(df_valide)
        assert len(resultat) == 2

    def test_schema_avec_check_isin(self):
        """
        Test 4: Schéma avec une contrainte "isin" (valeurs autorisées)
        """
        # ARRANGE
        schema_dict = {
            'status': {
                'type': 'str',
                'nullable': True,
                'checks': [{'isin': ['actif', 'inactif', 'en_attente']}]
            }
        }

        # ACT
        schema = build_dataframe_schema(schema_dict)

        # ASSERT
        df_valide = pd.DataFrame({'status': ['actif', 'inactif']})
        resultat = schema.validate(df_valide)
        assert len(resultat) == 2

    def test_schema_avec_unique(self):
        """
        Test 5: Schéma avec contrainte d'unicité
        """
        # ARRANGE
        schema_dict = {
            'id': {
                'type': 'int',
                'nullable': False,
                'unique': True
            }
        }

        # ACT
        schema = build_dataframe_schema(schema_dict)

        # ASSERT
        df_valide = pd.DataFrame({'id': [1, 2, 3]})
        resultat = schema.validate(df_valide)
        assert len(resultat) == 3

    def test_schema_strict_mode(self):
        """
        Test 6: Schéma en mode strict (colonnes supplémentaires interdites)
        """
        # ARRANGE
        schema_dict = {
            'nom': {'type': 'str', 'nullable': True}
        }

        # ACT
        schema = build_dataframe_schema(schema_dict, strict_method=True)

        # ASSERT
        assert schema.strict is True


# =============================================================================
#                Tests pour valider_csv()
# =============================================================================

class TestValiderCsv:
    """Tests pour la validation de fichiers CSV"""

    def test_validation_csv_valide(self, tmp_path):
        """
        Test 1: Validation d'un CSV entièrement valide
        """
        # ARRANGE - Créer un fichier CSV temporaire
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'nom': ['Alice', 'Bob', 'Charlie']
        })
        df.to_csv(csv_file, index=False)

        # Créer un schéma simple
        schema_dict = {
            'id': {'type': 'int', 'nullable': False},
            'nom': {'type': 'str', 'nullable': True}
        }
        schema = build_dataframe_schema(schema_dict)

        # Créer les répertoires de sortie
        (tmp_path / "data" / "raw_valid").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "raw_rejected").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "raw_errors").mkdir(parents=True, exist_ok=True)

        # ACT - Valider avec patch des chemins
        with patch('src.validation.schema_validation.Path') as mock_path:
            # Simuler les chemins
            mock_path.return_value = csv_file
            mock_path.side_effect = lambda x: Path(tmp_path) / x if "data/" in str(x) else Path(x)

            resultat = valider_csv(csv_file, schema, lazy=True)

        # ASSERT
        assert isinstance(resultat, pd.DataFrame)
        assert len(resultat) == 3

    def test_validation_csv_avec_erreurs(self, tmp_path):
        """
        Test 2: Validation d'un CSV avec des lignes invalides
        Les lignes invalides sont séparées dans un fichier rejeté
        """
        # ARRANGE
        csv_file = tmp_path / "test_errors.csv"
        df = pd.DataFrame({
            'id': [1, 'invalid', 3],  # 'invalid' n'est pas un int
            'nom': ['Alice', 'Bob', 'Charlie']
        })
        df.to_csv(csv_file, index=False)

        schema_dict = {
            'id': {'type': 'int', 'nullable': False},
            'nom': {'type': 'str', 'nullable': True}
        }
        schema = build_dataframe_schema(schema_dict)

        # Créer les répertoires
        for subdir in ['raw_valid', 'raw_rejected', 'raw_errors']:
            (tmp_path / "data" / subdir).mkdir(parents=True, exist_ok=True)

        # ACT
        with patch('src.validation.schema_validation.Path') as mock_path:
            mock_path.return_value = csv_file
            mock_path.side_effect = lambda x: Path(tmp_path) / x if "data/" in str(x) else Path(x)

            resultat = valider_csv(csv_file, schema, lazy=True)

        # ASSERT - Le résultat contient les lignes valides
        assert isinstance(resultat, pd.DataFrame)


# =============================================================================
#                Tests de validation de types
# =============================================================================

class TestTypeValidation:
    """Tests pour la validation des types de données"""

    def test_type_int(self):
        """Test: type int correctement validé"""
        schema_dict = {'col': {'type': 'int', 'nullable': True}}
        schema = build_dataframe_schema(schema_dict)

        df = pd.DataFrame({'col': [1, 2, 3]})
        resultat = schema.validate(df)
        assert len(resultat) == 3

    def test_type_str(self):
        """Test: type str correctement validé"""
        schema_dict = {'col': {'type': 'str', 'nullable': True}}
        schema = build_dataframe_schema(schema_dict)

        df = pd.DataFrame({'col': ['a', 'b', 'c']})
        resultat = schema.validate(df)
        assert len(resultat) == 3

    def test_type_float(self):
        """Test: type float correctement validé"""
        schema_dict = {'col': {'type': 'float', 'nullable': True}}
        schema = build_dataframe_schema(schema_dict)

        df = pd.DataFrame({'col': [1.5, 2.7, 3.9]})
        resultat = schema.validate(df)
        assert len(resultat) == 3

    def test_type_bool(self):
        """Test: type bool correctement validé"""
        schema_dict = {'col': {'type': 'bool', 'nullable': True}}
        schema = build_dataframe_schema(schema_dict)

        df = pd.DataFrame({'col': [True, False, True]})
        resultat = schema.validate(df)
        assert len(resultat) == 3

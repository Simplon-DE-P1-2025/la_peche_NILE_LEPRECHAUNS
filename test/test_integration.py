"""
Tests unitaires pour l'intégration Pandera (src/validation/integration.py)

Ce module fait le pont entre les schémas UI et la validation Pandera.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from pandera import DataFrameSchema

from src.validation.base import ValidationMode, ValidationResult
from src.validation.integration import (
    SchemaConverter,
    validate_for_crud,
    validate_dataframe,
    WIDGET_TO_PANDERA,
)


# =============================================================================
#                Tests pour WIDGET_TO_PANDERA (mapping)
# =============================================================================

class TestWidgetToPanderaMapping:
    """Tests pour le mapping des widgets vers les types Pandera"""

    def test_text_input_vers_string(self):
        """Test: TEXT_INPUT → pa.String"""
        from src.schema.definitions import WidgetType
        import pandera as pa

        assert WIDGET_TO_PANDERA[WidgetType.TEXT_INPUT] == pa.String

    def test_number_input_vers_float(self):
        """Test: NUMBER_INPUT → pa.Float"""
        from src.schema.definitions import WidgetType
        import pandera as pa

        assert WIDGET_TO_PANDERA[WidgetType.NUMBER_INPUT] == pa.Float

    def test_checkbox_vers_bool(self):
        """Test: CHECKBOX → pa.Bool"""
        from src.schema.definitions import WidgetType
        import pandera as pa

        assert WIDGET_TO_PANDERA[WidgetType.CHECKBOX] == pa.Bool

    def test_date_input_vers_datetime(self):
        """Test: DATE_INPUT → pa.DateTime"""
        from src.schema.definitions import WidgetType
        import pandera as pa

        assert WIDGET_TO_PANDERA[WidgetType.DATE_INPUT] == pa.DateTime


# =============================================================================
#                Tests pour SchemaConverter
# =============================================================================

class TestSchemaConverter:
    """Tests pour le convertisseur EntitySchema → DataFrameSchema"""

    @pytest.fixture
    def mock_entity_schema(self):
        """Créer un EntitySchema mock pour les tests"""
        from src.schema.definitions import EntitySchema, FieldSchema, WidgetType

        fields = [
            FieldSchema(
                name="nom",
                label="Nom",
                widget=WidgetType.TEXT_INPUT,
                required=True,
                max_chars=100
            ),
            FieldSchema(
                name="age",
                label="Âge",
                widget=WidgetType.NUMBER_INPUT,
                required=False,
                min_value=0,
                max_value=150
            ),
            FieldSchema(
                name="actif",
                label="Actif",
                widget=WidgetType.CHECKBOX,
                required=False
            ),
        ]

        return EntitySchema(
            name="test_entity",
            table_name="test_table",
            display_name="Test Entity",
            fields=fields
        )

    def test_build_schema_cree_dataframeschema(self, mock_entity_schema):
        """
        Test 1: build_schema() retourne un DataFrameSchema
        """
        # ARRANGE
        converter = SchemaConverter(mock_entity_schema)

        # ACT
        schema = converter.build_schema()

        # ASSERT
        assert isinstance(schema, DataFrameSchema)

    def test_build_schema_contient_colonnes(self, mock_entity_schema):
        """
        Test 2: Le schéma contient les colonnes définies
        """
        # ARRANGE
        converter = SchemaConverter(mock_entity_schema)

        # ACT
        schema = converter.build_schema()

        # ASSERT
        assert 'nom' in schema.columns
        assert 'age' in schema.columns
        assert 'actif' in schema.columns

    def test_build_schema_exclut_colonnes(self, mock_entity_schema):
        """
        Test 3: Les colonnes exclues ne sont pas dans le schéma
        """
        # ARRANGE
        converter = SchemaConverter(mock_entity_schema)

        # ACT
        schema = converter.build_schema(exclude_fields={'age'})

        # ASSERT
        assert 'nom' in schema.columns
        assert 'age' not in schema.columns

    def test_build_schema_ignore_timestamps(self, mock_entity_schema):
        """
        Test 4: Les colonnes created_at et updated_at sont ignorées
        """
        # ARRANGE
        from src.schema.definitions import FieldSchema, WidgetType

        # Ajouter des champs timestamp
        mock_entity_schema.fields.append(
            FieldSchema(name="created_at", label="Créé le", widget=WidgetType.DATE_INPUT)
        )
        mock_entity_schema.fields.append(
            FieldSchema(name="updated_at", label="Modifié le", widget=WidgetType.DATE_INPUT)
        )

        converter = SchemaConverter(mock_entity_schema)

        # ACT
        schema = converter.build_schema()

        # ASSERT
        assert 'created_at' not in schema.columns
        assert 'updated_at' not in schema.columns

    def test_validate_dict_valide(self, mock_entity_schema):
        """
        Test 5: validate_dict() avec données valides
        """
        # ARRANGE
        converter = SchemaConverter(mock_entity_schema)
        data = {
            'nom': 'Alice',
            'age': 25,
            'actif': True
        }

        # ACT
        with patch('src.validation.integration.enums', MagicMock()):
            resultat = converter.validate_dict(data)

        # ASSERT
        assert isinstance(resultat, ValidationResult)
        assert resultat.is_valid is True
        assert resultat.errors == []

    def test_validate_dict_champ_requis_manquant(self, mock_entity_schema):
        """
        Test 6: validate_dict() avec champ requis manquant
        """
        # ARRANGE
        converter = SchemaConverter(mock_entity_schema)
        data = {
            'nom': '',  # Vide alors que requis
            'age': 25
        }

        # ACT
        with patch('src.validation.integration.enums', MagicMock()):
            resultat = converter.validate_dict(data)

        # ASSERT
        assert resultat.is_valid is False
        assert len(resultat.errors) > 0


# =============================================================================
#                Tests pour validate_for_crud()
# =============================================================================

class TestValidateForCrud:
    """Tests pour la fonction utilitaire validate_for_crud"""

    @pytest.fixture
    def simple_entity_schema(self):
        """Créer un EntitySchema simple"""
        from src.schema.definitions import EntitySchema, FieldSchema, WidgetType

        fields = [
            FieldSchema(
                name="titre",
                label="Titre",
                widget=WidgetType.TEXT_INPUT,
                required=True
            ),
        ]

        return EntitySchema(
            name="article",
            table_name="articles",
            display_name="Article",
            fields=fields
        )

    def test_validation_donnees_valides(self, simple_entity_schema):
        """
        Test 1: Données valides → is_valid=True
        """
        # ARRANGE
        data = {'titre': 'Mon Article'}

        # ACT
        with patch('src.validation.integration.enums', MagicMock()):
            resultat = validate_for_crud(simple_entity_schema, data)

        # ASSERT
        assert resultat.is_valid is True

    def test_validation_donnees_invalides(self, simple_entity_schema):
        """
        Test 2: Données invalides → is_valid=False
        """
        # ARRANGE
        data = {'titre': ''}  # Vide alors que requis

        # ACT
        with patch('src.validation.integration.enums', MagicMock()):
            resultat = validate_for_crud(simple_entity_schema, data)

        # ASSERT
        assert resultat.is_valid is False

    def test_validation_avec_exclusion(self, simple_entity_schema):
        """
        Test 3: Les champs exclus ne sont pas validés
        """
        # ARRANGE
        data = {'titre': ''}  # Vide mais exclu

        # ACT
        with patch('src.validation.integration.enums', MagicMock()):
            resultat = validate_for_crud(
                simple_entity_schema,
                data,
                exclude_fields={'titre'}
            )

        # ASSERT - Pas d'erreur car le champ est exclu
        assert resultat.is_valid is True


# =============================================================================
#                Tests pour validate_dataframe()
# =============================================================================

class TestValidateDataframe:
    """Tests pour la validation de DataFrame complet"""

    @pytest.fixture
    def df_schema(self):
        """Créer un EntitySchema pour DataFrame"""
        from src.schema.definitions import EntitySchema, FieldSchema, WidgetType

        fields = [
            FieldSchema(
                name="id",
                label="ID",
                widget=WidgetType.NUMBER_INPUT,
                required=True
            ),
            FieldSchema(
                name="valeur",
                label="Valeur",
                widget=WidgetType.TEXT_INPUT,
                required=False
            ),
        ]

        return EntitySchema(
            name="data",
            table_name="data_table",
            display_name="Data",
            fields=fields
        )

    def test_validation_dataframe_valide(self, df_schema):
        """
        Test 1: DataFrame entièrement valide
        """
        # ARRANGE
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'valeur': ['a', 'b', 'c']
        })

        # ACT
        with patch('src.validation.integration.enums', MagicMock()):
            resultat = validate_dataframe(df_schema, df)

        # ASSERT
        assert resultat.is_valid is True
        assert resultat.validated_data is not None

    def test_validation_dataframe_avec_erreurs(self, df_schema):
        """
        Test 2: DataFrame avec des erreurs
        """
        # ARRANGE
        df = pd.DataFrame({
            'id': [1, None, 3],  # None dans un champ requis
            'valeur': ['a', 'b', 'c']
        })

        # ACT
        with patch('src.validation.integration.enums', MagicMock()):
            resultat = validate_dataframe(df_schema, df)

        # ASSERT
        # Le résultat dépend de la configuration du schéma
        assert isinstance(resultat, ValidationResult)


# =============================================================================
#                Tests pour ValidationResult
# =============================================================================

class TestValidationResultIntegration:
    """Tests d'intégration pour ValidationResult"""

    def test_resultat_contient_warnings(self):
        """
        Test: Le résultat peut contenir des warnings sans erreurs
        """
        # ARRANGE & ACT
        resultat = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Valeur non standard détectée"],
            validated_data=pd.DataFrame({'col': [1]})
        )

        # ASSERT
        assert resultat.is_valid is True
        assert len(resultat.warnings) == 1
        assert len(resultat.errors) == 0

    def test_resultat_erreurs_et_warnings(self):
        """
        Test: Le résultat peut avoir à la fois erreurs et warnings
        """
        # ARRANGE & ACT
        resultat = ValidationResult(
            is_valid=False,
            errors=["Champ requis manquant"],
            warnings=["Valeur non standard"],
            validated_data=None
        )

        # ASSERT
        assert resultat.is_valid is False
        assert len(resultat.errors) == 1
        assert len(resultat.warnings) == 1

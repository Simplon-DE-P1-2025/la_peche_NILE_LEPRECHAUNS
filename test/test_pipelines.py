"""
Tests unitaires pour les fonctions du pipeline (src/etl/pipelines.py)

Ce fichier teste les pipelines qui orchestrent l'extraction, validation et chargement.
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import pandas as pd


# =============================================================================
# Tests pour pipeline_db_raw()
# =============================================================================

class TestPipelineDbRaw:
    """Tests simples pour la fonction pipeline_db_raw"""

    @patch('src.etl.pipelines.load_df_to_db')               # Mock de la fonction de chargement en base
    @patch('src.etl.pipelines.create_postgres_engine')      # Mock de la création de l'engine    
    @patch('src.etl.pipelines.valider_csv')                 # Mock de la validation CSV
    @patch('src.etl.pipelines.build_dataframe_schema')      # Mock de la construction du schéma
    @patch('src.etl.pipelines.extract_url')                 # Mock de l'extraction des données
    @patch('src.etl.pipelines.load_config')                 # Mock du chargement de la config
    def test_pipeline_db_raw_execution_complete(
        self,
        mock_load_config,
        mock_extract_url,
        mock_build_schema,
        mock_valider_csv,
        mock_create_engine,
        mock_load_df_to_db
    ):
        """
        Test 1: Vérifier que pipeline_db_raw exécute toutes les étapes

        Ce test simule (mocke) toutes les dépendances externes pour vérifier
        que la fonction appelle bien toutes les étapes du pipeline.

        Étapes testées:
        1. Chargement de la configuration
        2. Extraction des données
        3. Construction du schéma de validation
        4. Validation des CSV
        5. Création de l'engine de base de données
        6. Chargement des données en base
        """
        # ARRANGE: Préparer les mocks

        # 1. Mock de la configuration
        mock_config = {
            'EXTRACT': {
                'dataset_url': 'https://example.com/data',
                'timeout_sec': 20,
                'output_dir': 'data'
            },
            'DATA_VALIDATION': {
                'fichier_test': {
                    'colonnes': ['col1', 'col2']
                }
            }
        }
        mock_load_config.return_value = mock_config

        # 2. Mock de l'extraction (retourne une liste de fichiers)
        mock_extract_url.return_value = [Path('data/fichier_test.csv')]

        # 3. Mock du schéma Pandera
        mock_schema = MagicMock()
        mock_build_schema.return_value = mock_schema

        # 4. Mock de la validation CSV (retourne un DataFrame)
        mock_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        mock_valider_csv.return_value = mock_df

        # 5. Mock de l'engine de base de données
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # ACT: Exécuter la fonction
        from src.etl.pipelines import pipeline_db_raw
        pipeline_db_raw()

        # ASSERT: Vérifier que toutes les étapes ont été appelées
        mock_load_config.assert_called_once_with("config/config.yml")
        mock_extract_url.assert_called_once()
        mock_build_schema.assert_called()
        mock_valider_csv.assert_called()
        mock_create_engine.assert_called()
        mock_load_df_to_db.assert_called()

    @patch('src.etl.pipelines.load_config')
    def test_pipeline_db_raw_charge_config(self, mock_load_config):
        """
        Test 2: Vérifier que le pipeline charge bien le fichier de configuration

        Ce test simple vérifie juste la première étape du pipeline.
        """
        # ARRANGE
        mock_load_config.return_value = {
            'EXTRACT': {'dataset_url': 'test', 'timeout_sec': 10, 'output_dir': 'data'},
            'DATA_VALIDATION': {}
        }

        # ACT & ASSERT
        # On s'attend à ce que load_config soit appelé avec le bon chemin
        from src.etl.pipelines import pipeline_db_raw

        # Pour ce test, on doit aussi mocker les autres fonctions
        # sinon le pipeline échouera
        with patch('src.etl.pipelines.extract_url'), \
             patch('src.etl.pipelines.build_dataframe_schema'), \
             patch('src.etl.pipelines.valider_csv'), \
             patch('src.etl.pipelines.create_postgres_engine'), \
             patch('src.etl.pipelines.load_df_to_db'):

            pipeline_db_raw()
            mock_load_config.assert_called_once_with("config/config.yml")


# =============================================================================
# Tests pour pipeline_db_cleaned()
# =============================================================================

class TestPipelineDbCleaned:
    """Tests simples pour la fonction pipeline_db_cleaned"""

    @patch('src.etl.pipelines.load_df_to_db')
    @patch('src.etl.pipelines.execute_sql_file')
    @patch('src.etl.pipelines.create_postgres_engine')
    @patch('src.etl.pipelines.valider_csv')
    @patch('src.etl.pipelines.build_dataframe_schema')
    @patch('src.etl.pipelines.extract_url')
    @patch('src.etl.pipelines.load_config')
    @patch('src.etl.pipelines.pd.merge')
    def test_pipeline_db_cleaned_execution_complete(
        self,
        mock_merge,
        mock_load_config,
        mock_extract_url,
        mock_build_schema,
        mock_valider_csv,
        mock_create_engine,
        mock_execute_sql,
        mock_load_df_to_db
    ):
        """
        Test 1: Vérifier que pipeline_db_cleaned exécute toutes les étapes

        Ce pipeline est plus complexe car il fait des jointures de DataFrames.
        """
        # ARRANGE: Préparer les mocks

        # Configuration
        mock_config = {
            'EXTRACT': {
                'dataset_url': 'https://example.com/data',
                'timeout_sec': 20,
                'output_dir': 'data'
            },
            'DATA_VALIDATION': {
                'operations': {'colonnes': ['operation_id']},
                'operations_stats': {'colonnes': ['operation_id']},
                'flotteurs': {'colonnes': ['id']},
                'resultats_humain': {'colonnes': ['id']}
            }
        }
        mock_load_config.return_value = mock_config

        # Extraction
        mock_extract_url.return_value = [
            Path('data/operations.csv'),
            Path('data/operations_stats.csv'),
            Path('data/flotteurs.csv'),
            Path('data/resultats_humain.csv')
        ]

        # Schémas
        mock_schema = MagicMock()
        mock_schema.columns.keys.return_value = ['col1', 'col2']
        mock_build_schema.return_value = mock_schema

        # DataFrames validés
        df_operations = pd.DataFrame({'operation_id': [1, 2]})
        df_stats = pd.DataFrame({'operation_id': [1, 2]})
        df_flotteurs = pd.DataFrame({'id': [1, 2]})
        df_resultats = pd.DataFrame({'id': [1, 2]})

        # Simuler les retours de valider_csv dans l'ordre
        mock_valider_csv.side_effect = [
            df_operations,
            df_stats,
            df_flotteurs,
            df_resultats
        ]

        # Merge des DataFrames
        df_merged = pd.DataFrame({'operation_id': [1, 2], 'data': ['a', 'b']})
        mock_merge.return_value = df_merged

        # Engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # ACT: Exécuter la fonction
        from src.etl.pipelines import pipeline_db_cleaned
        pipeline_db_cleaned()

        # ASSERT: Vérifier les étapes clés
        mock_load_config.assert_called_once_with("config/config_clean.yml")
        mock_extract_url.assert_called_once()
        assert mock_build_schema.call_count == 4  # 4 schémas
        assert mock_valider_csv.call_count == 4   # 4 validations
        mock_execute_sql.assert_called_once()
        assert mock_load_df_to_db.call_count >= 1  # Au moins 1 chargement



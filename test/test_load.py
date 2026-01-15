"""
Tests unitaires SIMPLES pour les fonctions de chargement (src/etl/load.py)

"""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from sqlalchemy.engine import Engine
from src.etl.load import load_df_to_db


# =============================================================================
#                Tests pour load_df_to_db() 
# =============================================================================

class TestLoadDfToDb:
    """Tests simples pour la fonction load_df_to_db"""

    def test_chargement_dataframe_simple(self):
        """
        Test 1: Vérifier que load_df_to_db fonctionne avec un DataFrame simple

        Ce test utilise un "mock" pour simuler la base de données.
        Un mock est un objet "faux" qui fait semblant d'être une vraie base de données.
        On n'a pas besoin d'une vraie base de données pour tester!

        Étapes:
        1. Créer un DataFrame de test
        2. Créer un mock de la base de données
        3. Appeler load_df_to_db()
        4. Vérifier que ça fonctionne (pas d'erreur)
        """
        # 1. ARRANGE: Préparer un DataFrame simple
        mon_dataframe = pd.DataFrame({
            'nom': ['Alice', 'Bob'],
            'age': [25, 30]
        })

        # Créer un faux moteur de base de données (mock)
        # MagicMock = objet qui fait semblant d'être n'importe quoi
        fausse_base_de_donnees = MagicMock(spec=Engine)

        # Configurer le mock pour qu'il se comporte comme une vraie connexion
        fausse_connexion = MagicMock()
        fausse_base_de_donnees.begin.return_value.__enter__ = MagicMock(return_value=fausse_connexion)
        fausse_base_de_donnees.begin.return_value.__exit__ = MagicMock(return_value=False)

        # 2. ACT: Appeler la fonction
        # Si ça ne lève pas d'erreur, c'est bon!
        load_df_to_db(
            df=mon_dataframe,
            table_name="ma_table",
            engine=fausse_base_de_donnees
        )

        # 3. ASSERT: Vérifier que la fonction a bien appelé begin()
        fausse_base_de_donnees.begin.assert_called_once()

    def test_chargement_dataframe_vide(self):
        """
        Test 2: Vérifier que la fonction gère un DataFrame vide

        Un DataFrame vide ne devrait pas causer d'erreur
        """
        # ARRANGE
        dataframe_vide = pd.DataFrame()  # Pas de données

        # Mock de la base de données
        fausse_base = MagicMock(spec=Engine)
        fausse_connexion = MagicMock()
        fausse_base.begin.return_value.__enter__ = MagicMock(return_value=fausse_connexion)
        fausse_base.begin.return_value.__exit__ = MagicMock(return_value=False)

        # ACT & ASSERT: Ne devrait pas lever d'erreur
        load_df_to_db(dataframe_vide, "table_vide", fausse_base)
        fausse_base.begin.assert_called_once()

    def test_chargement_avec_parametres(self):
        """
        Test 3: Vérifier qu'on peut passer des paramètres supplémentaires

        La fonction accepte des paramètres comme if_exists et schema
        """
        # ARRANGE
        mon_df = pd.DataFrame({'col': [1, 2, 3]})

        fausse_base = MagicMock(spec=Engine)
        fausse_connexion = MagicMock()
        fausse_base.begin.return_value.__enter__ = MagicMock(return_value=fausse_connexion)
        fausse_base.begin.return_value.__exit__ = MagicMock(return_value=False)

        # ACT: Utiliser des paramètres supplémentaires
        load_df_to_db(
            df=mon_df,
            table_name="ma_table",
            engine=fausse_base,
            if_exists="append",  # Ajouter à la table existante
            schema="public"       # Nom du schéma
        )

        # ASSERT
        fausse_base.begin.assert_called_once()




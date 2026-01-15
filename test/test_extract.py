"""
Tests unitaires SIMPLES pour les fonctions d'extraction (src/etl/extract.py)

"""
import pytest
import yaml
from pathlib import Path
from src.etl.extract import load_config


# =============================================================================
#               Tests pour load_config() 
# =============================================================================

class TestLoadConfig:
    """Tests simples pour la fonction load_config"""

    def test_load_config_avec_fichier_valide(self, tmp_path):
        """
        Test 1: Vérifier que load_config charge correctement un fichier YAML

        Étapes:
        1. Créer un fichier config.yml temporaire avec des données
        2. Appeler load_config() avec ce fichier
        3. Vérifier que les données sont correctement chargées
        """
        # 1. ARRANGE: Préparer les données de test
        config_file = tmp_path / "config.yml"  # tmp_path est fourni par pytest
        mes_donnees = {
            "nom": "mon_projet",
            "version": "1.0"
        }

        # Écrire le fichier config
        with open(config_file, "w") as f:
            yaml.dump(mes_donnees, f)

        # 2. ACT: Exécuter la fonction à tester
        resultat = load_config(str(config_file))

        # 3. ASSERT: Vérifier que le résultat est correct
        assert resultat == mes_donnees
        assert resultat["nom"] == "mon_projet"

    def test_load_config_fichier_inexistant(self):
        """
        Test 2: Vérifier que load_config lève une erreur si le fichier n'existe pas

        On s'attend à ce qu'une erreur FileNotFoundError soit levée
        """
        # Vérifier qu'une exception est levée
        with pytest.raises(FileNotFoundError) as erreur:
            load_config("fichier_qui_nexiste_pas.yml")

        # Vérifier le message d'erreur
        assert "Fichier de configuration introuvable" in str(erreur.value)


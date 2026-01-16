"""
Tests unitaires pour les validateurs cross-field (src/validation/validators.py)

Ces fonctions vérifient des règles métier impliquant plusieurs champs.
"""
import pytest
import pandas as pd
from src.validation.validators import (
    coordinates_check,
    coordinates_in_france,
    resultat_humain_coherence,
    flotteur_longueur_type_coherence,
    beaufort_scale_check,
    douglas_scale_check,
    departement_format_check,
)


# =============================================================================
#                Tests pour coordinates_check()
# =============================================================================

class TestCoordinatesCheck:
    """Tests pour la validation de cohérence latitude/longitude"""

    def test_coordonnees_valides_toutes_presentes(self):
        """
        Test 1: latitude et longitude sont toutes les deux présentes
        → Doit être valide
        """
        # ARRANGE
        df = pd.DataFrame({
            'latitude': [48.8566, 45.764],
            'longitude': [2.3522, 4.8357]
        })
        check = coordinates_check()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat is True

    def test_coordonnees_valides_toutes_absentes(self):
        """
        Test 2: latitude et longitude sont toutes les deux absentes (NULL)
        → Doit être valide
        """
        # ARRANGE
        df = pd.DataFrame({
            'latitude': [None, None],
            'longitude': [None, None]
        })
        check = coordinates_check()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat is True

    def test_coordonnees_invalides_latitude_seule(self):
        """
        Test 3: latitude présente mais longitude absente
        → Doit être invalide
        """
        # ARRANGE
        df = pd.DataFrame({
            'latitude': [48.8566, None],
            'longitude': [None, None]
        })
        check = coordinates_check()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat is False

    def test_colonnes_absentes(self):
        """
        Test 4: Colonnes latitude/longitude absentes du DataFrame
        → Doit retourner True (pas d'erreur)
        """
        # ARRANGE
        df = pd.DataFrame({'autre_colonne': [1, 2, 3]})
        check = coordinates_check()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat is True


# =============================================================================
#                Tests pour coordinates_in_france()
# =============================================================================

class TestCoordinatesInFrance:
    """Tests pour la validation géographique (zone France)"""

    def test_coordonnees_france_metropolitaine(self):
        """
        Test 1: Coordonnées dans la France métropolitaine
        → Doit être valide
        """
        # ARRANGE - Paris
        df = pd.DataFrame({
            'latitude': [48.8566],
            'longitude': [2.3522]
        })
        check = coordinates_in_france()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat.all()

    def test_coordonnees_reunion(self):
        """
        Test 2: Coordonnées à la Réunion
        → Doit être valide
        """
        # ARRANGE - La Réunion
        df = pd.DataFrame({
            'latitude': [-21.1151],
            'longitude': [55.5364]
        })
        check = coordinates_in_france()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat.all()

    def test_coordonnees_hors_france(self):
        """
        Test 3: Coordonnées hors zone France (New York)
        → Doit être invalide
        """
        # ARRANGE - New York
        df = pd.DataFrame({
            'latitude': [40.7128],
            'longitude': [-74.0060]
        })
        check = coordinates_in_france()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert not resultat.all()

    def test_coordonnees_nulles(self):
        """
        Test 4: Coordonnées nulles
        → Doit être valide (null autorisé)
        """
        # ARRANGE
        df = pd.DataFrame({
            'latitude': [None],
            'longitude': [None]
        })
        check = coordinates_in_france()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat.all()


# =============================================================================
#                Tests pour beaufort_scale_check()
# =============================================================================

class TestBeaufortScaleCheck:
    """Tests pour l'échelle de Beaufort (force du vent 0-12)"""

    def test_valeur_valide_minimum(self):
        """Test avec la valeur minimum (0)"""
        check = beaufort_scale_check()
        assert check._check_fn(0) is True

    def test_valeur_valide_maximum(self):
        """Test avec la valeur maximum (12)"""
        check = beaufort_scale_check()
        assert check._check_fn(12) is True

    def test_valeur_valide_milieu(self):
        """Test avec une valeur au milieu (6)"""
        check = beaufort_scale_check()
        assert check._check_fn(6) is True

    def test_valeur_invalide_trop_haute(self):
        """Test avec une valeur trop haute (13)"""
        check = beaufort_scale_check()
        assert check._check_fn(13) is False

    def test_valeur_invalide_negative(self):
        """Test avec une valeur négative (-1)"""
        check = beaufort_scale_check()
        assert check._check_fn(-1) is False

    def test_valeur_nulle(self):
        """Test avec une valeur nulle (None)"""
        check = beaufort_scale_check()
        assert check._check_fn(None) is True


# =============================================================================
#                Tests pour douglas_scale_check()
# =============================================================================

class TestDouglasScaleCheck:
    """Tests pour l'échelle de Douglas (force de la mer 0-9)"""

    def test_valeur_valide_minimum(self):
        """Test avec la valeur minimum (0)"""
        check = douglas_scale_check()
        assert check._check_fn(0) is True

    def test_valeur_valide_maximum(self):
        """Test avec la valeur maximum (9)"""
        check = douglas_scale_check()
        assert check._check_fn(9) is True

    def test_valeur_invalide_trop_haute(self):
        """Test avec une valeur trop haute (10)"""
        check = douglas_scale_check()
        assert check._check_fn(10) is False

    def test_valeur_nulle(self):
        """Test avec une valeur nulle"""
        check = douglas_scale_check()
        assert check._check_fn(None) is True


# =============================================================================
#                Tests pour departement_format_check()
# =============================================================================

class TestDepartementFormatCheck:
    """Tests pour le format du département (2-3 caractères)"""

    def test_departement_valide_deux_chiffres(self):
        """Test avec un département à 2 chiffres (75 - Paris)"""
        check = departement_format_check()
        assert check._check_fn("75") is True

    def test_departement_valide_trois_chiffres(self):
        """Test avec un département à 3 chiffres (971 - Guadeloupe)"""
        check = departement_format_check()
        assert check._check_fn("971") is True

    def test_departement_valide_corse(self):
        """Test avec la Corse (2A)"""
        check = departement_format_check()
        assert check._check_fn("2A") is True

    def test_departement_invalide_trop_long(self):
        """Test avec un code trop long"""
        check = departement_format_check()
        assert check._check_fn("12345") is False

    def test_departement_vide(self):
        """Test avec une chaîne vide"""
        check = departement_format_check()
        assert check._check_fn("") is True

    def test_departement_null(self):
        """Test avec None"""
        check = departement_format_check()
        assert check._check_fn(None) is True


# =============================================================================
#                Tests pour resultat_humain_coherence()
# =============================================================================

class TestResultatHumainCoherence:
    """Tests pour la cohérence resultat_humain / nombre de personnes"""

    def test_coherence_valide_avec_resultat_et_nombre(self):
        """
        Test: Si un résultat est spécifié, le nombre doit être >= 1
        """
        # ARRANGE
        df = pd.DataFrame({
            'resultat_humain': ['Sauvé', 'Décédé'],
            'nombre': [5, 1]
        })
        check = resultat_humain_coherence()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat is True

    def test_coherence_invalide_resultat_sans_nombre(self):
        """
        Test: Résultat spécifié mais nombre = 0
        → Doit être invalide
        """
        # ARRANGE
        df = pd.DataFrame({
            'resultat_humain': ['Sauvé'],
            'nombre': [0]
        })
        check = resultat_humain_coherence()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat is False

    def test_coherence_valide_sans_resultat(self):
        """
        Test: Pas de résultat, nombre peut être 0
        → Doit être valide
        """
        # ARRANGE
        df = pd.DataFrame({
            'resultat_humain': [None, ''],
            'nombre': [0, 0]
        })
        check = resultat_humain_coherence()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat is True


# =============================================================================
#                Tests pour flotteur_longueur_type_coherence()
# =============================================================================

class TestFlotteurLongueurTypeCoherence:
    """Tests pour la cohérence type de flotteur / longueur"""

    def test_kayak_longueur_valide(self):
        """
        Test: Un kayak de 4m est valide (max 6m)
        """
        # ARRANGE
        df = pd.DataFrame({
            'type_flotteur': ['Canoe/Kayak'],
            'longueur': [4.0]
        })
        check = flotteur_longueur_type_coherence()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat.all()

    def test_kayak_longueur_invalide(self):
        """
        Test: Un kayak de 10m est invalide (max 6m)
        """
        # ARRANGE
        df = pd.DataFrame({
            'type_flotteur': ['Canoe/Kayak'],
            'longueur': [10.0]
        })
        check = flotteur_longueur_type_coherence()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert not resultat.all()

    def test_longueur_nulle_toujours_valide(self):
        """
        Test: Une longueur nulle est toujours valide
        """
        # ARRANGE
        df = pd.DataFrame({
            'type_flotteur': ['Jet-ski'],
            'longueur': [None]
        })
        check = flotteur_longueur_type_coherence()

        # ACT
        resultat = check._check_fn(df)

        # ASSERT
        assert resultat.all()

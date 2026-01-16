"""
Tests unitaires pour les classes de base de validation (src/validation/base.py)

Ce module fournit les utilitaires pour créer des schémas Pandera.
"""
import pytest
import pandas as pd
import pandera as pa
from pandera import Column

from src.validation.base import (
    ValidationMode,
    ValidationResult,
    EnumWarningCollector,
    create_enum_check_warning,
    create_enum_column,
)


# =============================================================================
#                Tests pour ValidationMode (Enum)
# =============================================================================

class TestValidationMode:
    """Tests pour l'enum ValidationMode"""

    def test_mode_strict_existe(self):
        """Test: le mode STRICT existe"""
        assert ValidationMode.STRICT.value == "strict"

    def test_mode_warning_existe(self):
        """Test: le mode WARNING existe"""
        assert ValidationMode.WARNING.value == "warning"


# =============================================================================
#                Tests pour ValidationResult (Dataclass)
# =============================================================================

class TestValidationResult:
    """Tests pour la dataclass ValidationResult"""

    def test_creation_resultat_valide(self):
        """
        Test 1: Création d'un résultat de validation valide
        """
        # ARRANGE & ACT
        resultat = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            validated_data=pd.DataFrame({'col': [1, 2]})
        )

        # ASSERT
        assert resultat.is_valid is True
        assert resultat.errors == []
        assert resultat.warnings == []
        assert resultat.validated_data is not None

    def test_creation_resultat_invalide_avec_erreurs(self):
        """
        Test 2: Création d'un résultat avec des erreurs
        """
        # ARRANGE & ACT
        resultat = ValidationResult(
            is_valid=False,
            errors=["Erreur 1", "Erreur 2"],
            warnings=["Warning 1"],
            validated_data=None
        )

        # ASSERT
        assert resultat.is_valid is False
        assert len(resultat.errors) == 2
        assert len(resultat.warnings) == 1
        assert resultat.validated_data is None

    def test_valeurs_par_defaut(self):
        """
        Test 3: Les listes errors et warnings sont vides par défaut
        """
        # ARRANGE & ACT
        resultat = ValidationResult(is_valid=True)

        # ASSERT
        assert resultat.errors == []
        assert resultat.warnings == []


# =============================================================================
#                Tests pour EnumWarningCollector
# =============================================================================

class TestEnumWarningCollector:
    """Tests pour le collecteur de warnings enum"""

    def test_initialisation_vide(self):
        """
        Test 1: Le collecteur est vide à l'initialisation
        """
        # ARRANGE & ACT
        collector = EnumWarningCollector()

        # ASSERT
        assert collector.warnings == []

    def test_check_enum_valeurs_valides(self):
        """
        Test 2: Pas de warning si les valeurs sont dans la liste autorisée
        """
        # ARRANGE
        collector = EnumWarningCollector()
        series = pd.Series(['actif', 'inactif'])
        allowed = ['actif', 'inactif', 'suspendu']

        # ACT
        collector.check_enum(series, allowed, 'status', 'Statut')

        # ASSERT
        assert collector.warnings == []

    def test_check_enum_valeur_non_standard(self):
        """
        Test 3: Warning généré si une valeur n'est pas dans la liste
        """
        # ARRANGE
        collector = EnumWarningCollector()
        series = pd.Series(['actif', 'inconnu'])  # 'inconnu' n'est pas autorisé
        allowed = ['actif', 'inactif', 'suspendu']

        # ACT
        collector.check_enum(series, allowed, 'status', 'Statut')

        # ASSERT
        assert len(collector.warnings) == 1
        assert 'inconnu' in collector.warnings[0]
        assert 'Statut' in collector.warnings[0]

    def test_check_enum_valeurs_nulles_ignorees(self):
        """
        Test 4: Les valeurs nulles ne génèrent pas de warning
        """
        # ARRANGE
        collector = EnumWarningCollector()
        series = pd.Series(['actif', None, ''])
        allowed = ['actif', 'inactif']

        # ACT
        collector.check_enum(series, allowed, 'status', 'Statut')

        # ASSERT
        assert collector.warnings == []

    def test_clear_reinitialise(self):
        """
        Test 5: La méthode clear() vide les warnings
        """
        # ARRANGE
        collector = EnumWarningCollector()
        series = pd.Series(['inconnu'])
        collector.check_enum(series, ['valide'], 'field', 'Field')
        assert len(collector.warnings) == 1

        # ACT
        collector.clear()

        # ASSERT
        assert collector.warnings == []

    def test_warnings_retourne_copie(self):
        """
        Test 6: La propriété warnings retourne une copie (pas la liste originale)
        """
        # ARRANGE
        collector = EnumWarningCollector()
        series = pd.Series(['inconnu'])
        collector.check_enum(series, ['valide'], 'field', 'Field')

        # ACT
        warnings = collector.warnings
        warnings.append("Nouveau warning")

        # ASSERT - La liste interne n'est pas modifiée
        assert len(collector.warnings) == 1


# =============================================================================
#                Tests pour create_enum_check_warning()
# =============================================================================

class TestCreateEnumCheckWarning:
    """Tests pour la création de checks enum en mode WARNING"""

    def test_check_retourne_toujours_vrai(self):
        """
        Test 1: Le check retourne toujours True (pas de blocage)
        """
        # ARRANGE
        check = create_enum_check_warning(['a', 'b', 'c'], 'field_name')
        series = pd.Series(['a', 'b', 'invalide'])  # 'invalide' n'est pas dans la liste

        # ACT
        resultat = check._check_fn(series)

        # ASSERT - Toujours True car mode WARNING
        assert resultat.all()

    def test_check_a_un_nom(self):
        """
        Test 2: Le check a un nom descriptif
        """
        # ARRANGE & ACT
        check = create_enum_check_warning(['a', 'b'], 'mon_champ')

        # ASSERT
        assert 'enum_warning_mon_champ' in check.name


# =============================================================================
#                Tests pour create_enum_column()
# =============================================================================

class TestCreateEnumColumn:
    """Tests pour la création de colonnes enum"""

    def test_creation_colonne_mode_strict(self):
        """
        Test 1: Mode STRICT - erreur si valeur hors liste
        """
        # ARRANGE & ACT
        column = create_enum_column(
            'status',
            ['actif', 'inactif'],
            mode=ValidationMode.STRICT
        )

        # ASSERT
        assert isinstance(column, Column)

    def test_creation_colonne_mode_warning(self):
        """
        Test 2: Mode WARNING - pas de blocage
        """
        # ARRANGE & ACT
        column = create_enum_column(
            'status',
            ['actif', 'inactif'],
            mode=ValidationMode.WARNING
        )

        # ASSERT
        assert isinstance(column, Column)

    def test_colonne_nullable_par_defaut(self):
        """
        Test 3: La colonne est nullable par défaut
        """
        # ARRANGE & ACT
        column = create_enum_column('field', ['a', 'b'])

        # ASSERT
        assert column.nullable is True

    def test_colonne_non_nullable(self):
        """
        Test 4: La colonne peut être configurée comme non nullable
        """
        # ARRANGE & ACT
        column = create_enum_column('field', ['a', 'b'], nullable=False)

        # ASSERT
        assert column.nullable is False

    def test_mode_warning_par_defaut(self):
        """
        Test 5: Le mode WARNING est utilisé par défaut
        """
        # ARRANGE & ACT
        column = create_enum_column('field', ['a', 'b'])

        # ASSERT - En mode WARNING, le check ne bloque pas
        # On vérifie que le check a le nom "enum_warning_"
        check_names = [c.name for c in column.checks]
        assert any('enum_warning' in name for name in check_names)

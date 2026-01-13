"""Definitions des schemas pour generation de formulaires.

Ce module contient les dataclasses qui definissent la structure
des formulaires et listes de l'application.

Usage:
    from src.schema.definitions import FieldSchema, EntitySchema, WidgetType

    field = FieldSchema(
        name="operation_id",
        label="ID Operation",
        widget=WidgetType.NUMBER_INPUT,
        required=True,
    )
"""

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
from typing import Any, Callable, List, Optional


class WidgetType(Enum):
    """Types de widgets Streamlit disponibles."""

    TEXT_INPUT = "text_input"
    NUMBER_INPUT = "number_input"
    SELECTBOX = "selectbox"
    MULTISELECT = "multiselect"
    DATE_INPUT = "date_input"
    TIME_INPUT = "time_input"
    TEXT_AREA = "text_area"
    CHECKBOX = "checkbox"


@dataclass
class FieldSchema:
    """Definition d'un champ de formulaire.

    Attributes:
        name: Nom du champ (doit correspondre au modele SQLAlchemy)
        label: Label en francais pour l'UI
        widget: Type de widget Streamlit
        required: Champ obligatoire
        min_value: Valeur minimum (pour NUMBER_INPUT)
        max_value: Valeur maximum (pour NUMBER_INPUT)
        max_chars: Longueur max (pour TEXT_INPUT)
        step: Pas d'increment (pour NUMBER_INPUT)
        enum_ref: Reference a une liste dans enums.py
        options: Options statiques (alternative a enum_ref)
        help_text: Texte d'aide
        placeholder: Placeholder pour le champ
        default: Valeur par defaut
        format_str: Format d'affichage (ex: "%.6f" pour Decimal)
        section: Groupe/section dans le formulaire
        order: Ordre d'affichage dans la section
        visible_in_list: Afficher dans la liste/DataFrame
        list_order: Ordre dans la liste
        list_width: Largeur de colonne en pixels
        formatter: Fonction de formatage personnalisee
        editable: Champ modifiable en mode edition
    """

    # Identification
    name: str
    label: str

    # Widget
    widget: WidgetType = WidgetType.TEXT_INPUT

    # Validation
    required: bool = False
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    max_chars: Optional[int] = None
    step: Optional[Any] = None

    # Enum/Options
    enum_ref: Optional[str] = None
    options: Optional[List[Any]] = None

    # Affichage
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    default: Any = None
    format_str: Optional[str] = None

    # Organisation
    section: str = "general"
    order: int = 0

    # Liste/Table
    visible_in_list: bool = True
    list_order: int = 0
    list_width: Optional[int] = None

    # Formatage
    formatter: Optional[Callable[[Any], Any]] = None

    # Editabilite
    editable: bool = True


@dataclass
class FormSection:
    """Definition d'une section de formulaire.

    Attributes:
        name: Identifiant technique de la section
        label: Label affiche en francais
        columns: Nombre de colonnes dans la section
        collapsible: Section repliable (expander)
        expanded: Etat initial si collapsible
        order: Ordre d'affichage
    """

    name: str
    label: str
    columns: int = 2
    collapsible: bool = False
    expanded: bool = True
    order: int = 0


@dataclass
class EntitySchema:
    """Schema complet d'une entite.

    Attributes:
        name: Nom technique (operation, flotteur, etc.)
        model_class: Nom de la classe SQLAlchemy
        crud_instance: Nom de l'instance CRUD (ex: crud_operation)
        primary_key: Nom du champ ID
        display_name: Nom affiche en francais (singulier)
        display_name_plural: Nom affiche en francais (pluriel)
        fields: Liste des champs
        sections: Liste des sections
        parent_entity: Pour entites enfants (flotteur -> operation)
        parent_fk_field: Nom du champ FK vers le parent
    """

    name: str
    model_class: str
    crud_instance: str
    primary_key: str
    display_name: str
    display_name_plural: str

    fields: List[FieldSchema] = dataclass_field(default_factory=list)
    sections: List[FormSection] = dataclass_field(default_factory=list)

    parent_entity: Optional[str] = None
    parent_fk_field: Optional[str] = None

    def get_field(self, name: str) -> Optional[FieldSchema]:
        """Recupere un champ par son nom."""
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def get_fields_by_section(self, section: str) -> List[FieldSchema]:
        """Recupere les champs d'une section, tries par ordre."""
        return sorted(
            [f for f in self.fields if f.section == section], key=lambda f: f.order
        )

    def get_list_fields(self) -> List[FieldSchema]:
        """Recupere les champs visibles dans la liste, tries par ordre."""
        return sorted(
            [f for f in self.fields if f.visible_in_list], key=lambda f: f.list_order
        )

    def get_sections_ordered(self) -> List[FormSection]:
        """Recupere les sections triees par ordre."""
        return sorted(self.sections, key=lambda s: s.order)

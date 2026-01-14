"""Schema de l'entite ResultatHumain.

Ce fichier definit le schema complet pour les resultats
humains (bilans des personnes impliquees).
"""

from src.schema.definitions import (
    EntitySchema,
    FieldSchema,
    FormSection,
    WidgetType,
)
from src.database.enums import get_resultat_emoji


def _format_resultat_with_emoji(value: str) -> str:
    """Formate le resultat avec son emoji."""
    if not value:
        return "-"
    emoji = get_resultat_emoji(value)
    return f"{emoji} {value}"

RESULTAT_HUMAIN_SCHEMA = EntitySchema(
    name="resultat_humain",
    model_class="ResultatHumain",
    crud_instance="crud_resultat_humain",
    primary_key="resultat_id",
    display_name="Resultat humain",
    display_name_plural="Resultats humains",
    parent_entity="operation",
    parent_fk_field="operation_id",
    sections=[
        FormSection(
            name="general",
            label="Informations",
            columns=2,
            order=1,
        ),
    ],
    fields=[
        FieldSchema(
            name="resultat_id",
            label="ID",
            widget=WidgetType.NUMBER_INPUT,
            required=False,  # Auto-genere
            help_text="Identifiant auto-genere",
            section="general",
            order=1,
            visible_in_list=True,
            list_order=1,
            editable=False,
        ),
        FieldSchema(
            name="operation_id",
            label="ID Operation",
            widget=WidgetType.NUMBER_INPUT,
            required=True,
            help_text="Operation parente",
            section="general",
            order=2,
            visible_in_list=False,
            editable=False,  # Lie au parent
        ),
        FieldSchema(
            name="categorie_personne",
            label="Categorie de personne",
            widget=WidgetType.SELECTBOX,
            enum_ref="CATEGORIE_PERSONNE",
            help_text="Type de personne (equipage, passager, etc.)",
            section="general",
            order=3,
            visible_in_list=True,
            list_order=2,
        ),
        FieldSchema(
            name="resultat_humain",
            label="Resultat",
            widget=WidgetType.SELECTBOX,
            enum_ref="RESULTAT_HUMAIN",
            help_text="Etat de la personne (sain et sauf, blesse, etc.)",
            section="general",
            order=4,
            visible_in_list=True,
            list_order=3,
            formatter=_format_resultat_with_emoji,
        ),
        FieldSchema(
            name="nombre",
            label="Nombre",
            widget=WidgetType.NUMBER_INPUT,
            min_value=0,
            step=1,
            default=0,
            required=True,
            help_text="Nombre de personnes dans cette categorie",
            section="general",
            order=5,
            visible_in_list=True,
            list_order=4,
        ),
        FieldSchema(
            name="dont_nombre_blesse",
            label="Dont blesses",
            widget=WidgetType.NUMBER_INPUT,
            min_value=0,
            step=1,
            default=0,
            help_text="Nombre de blesses parmi les personnes",
            section="general",
            order=6,
            visible_in_list=True,
            list_order=5,
        ),
    ],
)

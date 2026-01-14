"""Schema de l'entite Flotteur.

Ce fichier definit le schema complet pour les flotteurs
(embarcations impliquees dans les operations).
"""

from src.schema.definitions import (
    EntitySchema,
    FieldSchema,
    FormSection,
    WidgetType,
)

FLOTTEUR_SCHEMA = EntitySchema(
    name="flotteur",
    model_class="Flotteur",
    crud_instance="crud_flotteur",
    primary_key="flotteur_id",
    display_name="Flotteur",
    display_name_plural="Flotteurs",
    parent_entity="operation",
    parent_fk_field="operation_id",
    sections=[
        FormSection(
            name="identification",
            label="Identification",
            columns=2,
            order=1,
        ),
        FormSection(
            name="caracteristiques",
            label="Caracteristiques",
            columns=2,
            order=2,
        ),
        FormSection(
            name="bilan",
            label="Bilan",
            columns=2,
            order=3,
        ),
    ],
    fields=[
        # =====================================================================
        # Section: Identification
        # =====================================================================
        FieldSchema(
            name="flotteur_id",
            label="ID Flotteur",
            widget=WidgetType.NUMBER_INPUT,
            required=False,  # Auto-genere
            help_text="Identifiant auto-genere",
            section="identification",
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
            section="identification",
            order=2,
            visible_in_list=False,
            editable=False,  # Lie au parent
        ),
        FieldSchema(
            name="type_flotteur",
            label="Type de flotteur",
            widget=WidgetType.SELECTBOX,
            enum_ref="TYPE_FLOTTEUR",
            help_text="Type d'embarcation",
            section="identification",
            order=3,
            visible_in_list=True,
            list_order=2,
        ),
        FieldSchema(
            name="categorie_flotteur",
            label="Categorie",
            widget=WidgetType.TEXT_INPUT,
            max_chars=100,
            help_text="Categorie du flotteur",
            section="identification",
            order=4,
            visible_in_list=True,
            list_order=3,
        ),
        # =====================================================================
        # Section: Caracteristiques
        # =====================================================================
        FieldSchema(
            name="pavillon",
            label="Pavillon",
            widget=WidgetType.TEXT_INPUT,
            max_chars=50,
            default="France",
            help_text="Pays d'immatriculation",
            section="caracteristiques",
            order=1,
            visible_in_list=True,
            list_order=4,
        ),
        FieldSchema(
            name="immatriculation",
            label="Immatriculation",
            widget=WidgetType.TEXT_INPUT,
            max_chars=50,
            help_text="Numero d'immatriculation",
            section="caracteristiques",
            order=2,
            visible_in_list=False,
        ),
        # =====================================================================
        # Section: Bilan
        # =====================================================================
        FieldSchema(
            name="resultat_flotteur",
            label="Resultat",
            widget=WidgetType.SELECTBOX,
            enum_ref="RESULTAT_FLOTTEUR",
            help_text="Etat final du flotteur",
            section="bilan",
            order=1,
            visible_in_list=True,
            list_order=5,
        ),
    ],
)

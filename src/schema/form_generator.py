"""Generateur de formulaires Streamlit a partir de schemas.

Ce module genere automatiquement les widgets Streamlit
a partir des definitions de champs.

Usage:
    from src.schema import FormGenerator
    from src.schema.schemas import OPERATION_SCHEMA

    gen = FormGenerator(OPERATION_SCHEMA)
    values = gen.render_form("create_op", current_values=None)
    is_valid, errors = gen.validate(values)
    cleaned = gen.clean_values(values)
"""

import streamlit as st
from datetime import date, time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from src.schema.definitions import EntitySchema, FieldSchema, WidgetType
from src.database import enums


class FormGenerator:
    """Generateur de formulaires Streamlit a partir de schemas."""

    def __init__(self, schema: EntitySchema):
        """Initialise le generateur avec un schema.

        Args:
            schema: Schema de l'entite
        """
        self.schema = schema
        self._enum_cache: Dict[str, list] = {}

    def _get_enum_options(self, enum_ref: str) -> list:
        """Recupere les options d'un enum par son nom.

        Args:
            enum_ref: Nom de la variable enum dans enums.py

        Returns:
            Liste des options
        """
        if enum_ref not in self._enum_cache:
            self._enum_cache[enum_ref] = getattr(enums, enum_ref, [])
        return self._enum_cache[enum_ref]

    def _render_widget(
        self,
        field: FieldSchema,
        key_prefix: str,
        current_value: Any = None,
        disabled: bool = False,
    ) -> Any:
        """Rend un widget Streamlit pour un champ.

        Args:
            field: Definition du champ
            key_prefix: Prefixe pour la cle Streamlit
            current_value: Valeur actuelle (mode edition)
            disabled: Widget desactive

        Returns:
            Valeur du widget
        """
        widget_key = f"{key_prefix}_{field.name}"

        # Determiner la valeur initiale
        value = current_value if current_value is not None else field.default

        # Construire le label avec asterisque si requis
        label = f"{field.label} *" if field.required else field.label

        # Render selon le type de widget
        if field.widget == WidgetType.TEXT_INPUT:
            return st.text_input(
                label,
                value=value or "",
                max_chars=field.max_chars,
                help=field.help_text,
                placeholder=field.placeholder,
                key=widget_key,
                disabled=disabled,
            )

        elif field.widget == WidgetType.NUMBER_INPUT:
            # Gerer les types numeriques
            if isinstance(value, Decimal):
                value = float(value)

            # Determiner le format
            format_str = field.format_str
            if format_str is None:
                # Detecter si on veut des decimales
                if field.step and isinstance(field.step, float):
                    format_str = "%.2f"
                elif any(
                    x is not None and isinstance(x, float)
                    for x in [field.min_value, field.max_value]
                ):
                    format_str = "%.2f"

            # Calculate default value respecting min_value
            default_value = value if value is not None else field.default
            if default_value is None:
                default_value = field.min_value if field.min_value is not None else 0
            elif field.min_value is not None and default_value < field.min_value:
                default_value = field.min_value

            kwargs = {
                "label": label,
                "value": default_value,
                "help": field.help_text,
                "key": widget_key,
                "disabled": disabled,
            }

            if field.min_value is not None:
                kwargs["min_value"] = field.min_value
            if field.max_value is not None:
                kwargs["max_value"] = field.max_value
            if field.step is not None:
                kwargs["step"] = field.step
            if format_str:
                kwargs["format"] = format_str

            return st.number_input(**kwargs)

        elif field.widget == WidgetType.SELECTBOX:
            options = field.options or []
            if field.enum_ref:
                options = self._get_enum_options(field.enum_ref)

            # Option vide au debut si non requis
            if not field.required:
                options = [""] + list(options)

            # Trouver l'index de la valeur actuelle
            index = 0
            if value and value in options:
                index = options.index(value)

            return st.selectbox(
                label,
                options=options,
                index=index,
                help=field.help_text,
                key=widget_key,
                disabled=disabled,
            )

        elif field.widget == WidgetType.DATE_INPUT:
            if value is None:
                value = date.today()
            return st.date_input(
                label,
                value=value,
                help=field.help_text,
                key=widget_key,
                disabled=disabled,
            )

        elif field.widget == WidgetType.TIME_INPUT:
            if value is None:
                value = time(0, 0)
            return st.time_input(
                label,
                value=value,
                help=field.help_text,
                key=widget_key,
                disabled=disabled,
            )

        elif field.widget == WidgetType.TEXT_AREA:
            return st.text_area(
                label,
                value=value or "",
                help=field.help_text,
                key=widget_key,
                disabled=disabled,
            )

        elif field.widget == WidgetType.CHECKBOX:
            return st.checkbox(
                label,
                value=bool(value) if value is not None else False,
                help=field.help_text,
                key=widget_key,
                disabled=disabled,
            )

        elif field.widget == WidgetType.MULTISELECT:
            options = field.options or []
            if field.enum_ref:
                options = self._get_enum_options(field.enum_ref)
            return st.multiselect(
                label,
                options=options,
                default=value or [],
                help=field.help_text,
                key=widget_key,
                disabled=disabled,
            )

        return None

    def render_form(
        self,
        key_prefix: str,
        current_values: Optional[Dict[str, Any]] = None,
        exclude_fields: Optional[Set[str]] = None,
        include_fields: Optional[Set[str]] = None,
        disabled_fields: Optional[Set[str]] = None,
        show_sections: bool = True,
    ) -> Dict[str, Any]:
        """Rend un formulaire complet et retourne les valeurs.

        Args:
            key_prefix: Prefixe pour les cles Streamlit
            current_values: Valeurs actuelles (mode edition)
            exclude_fields: Champs a exclure
            include_fields: Si specifie, seuls ces champs sont inclus
            disabled_fields: Champs en lecture seule
            show_sections: Afficher les titres de sections

        Returns:
            Dictionnaire des valeurs du formulaire
        """
        current_values = current_values or {}
        exclude_fields = exclude_fields or set()
        disabled_fields = disabled_fields or set()

        # Toujours exclure les timestamps
        exclude_fields = exclude_fields | {"created_at", "updated_at"}

        # Filtrer les champs
        fields = [f for f in self.schema.fields if f.name not in exclude_fields]
        if include_fields:
            fields = [f for f in fields if f.name in include_fields]

        # Grouper par section
        sections: Dict[str, List[FieldSchema]] = {}
        for field in fields:
            section = field.section
            if section not in sections:
                sections[section] = []
            sections[section].append(field)

        # Trier chaque section par ordre
        for section in sections:
            sections[section].sort(key=lambda f: f.order)

        # Recuperer les definitions de sections
        section_defs = {s.name: s for s in self.schema.sections}

        result = {}

        # Rendre chaque section dans l'ordre defini
        ordered_sections = self.schema.get_sections_ordered()
        for section_def in ordered_sections:
            section_name = section_def.name
            if section_name not in sections:
                continue

            section_fields = sections[section_name]

            # Rendre la section
            if section_def.collapsible:
                with st.expander(section_def.label, expanded=section_def.expanded):
                    self._render_section_fields(
                        section_fields,
                        section_def.columns,
                        key_prefix,
                        current_values,
                        disabled_fields,
                        result,
                    )
            else:
                if show_sections and section_def.label:
                    st.markdown(f"**{section_def.label}**")
                self._render_section_fields(
                    section_fields,
                    section_def.columns,
                    key_prefix,
                    current_values,
                    disabled_fields,
                    result,
                )

        # Rendre les champs sans section definie (section "general")
        remaining_sections = set(sections.keys()) - {s.name for s in ordered_sections}
        for section_name in remaining_sections:
            section_fields = sections[section_name]
            cols = st.columns(2)
            for i, field in enumerate(section_fields):
                with cols[i % 2]:
                    value = self._render_widget(
                        field,
                        key_prefix,
                        current_values.get(field.name),
                        disabled=field.name in disabled_fields or not field.editable,
                    )
                    result[field.name] = value

        return result

    def _render_section_fields(
        self,
        fields: List[FieldSchema],
        num_columns: int,
        key_prefix: str,
        current_values: Dict[str, Any],
        disabled_fields: Set[str],
        result: Dict[str, Any],
    ) -> None:
        """Rend les champs d'une section.

        Args:
            fields: Liste des champs de la section
            num_columns: Nombre de colonnes
            key_prefix: Prefixe pour les cles
            current_values: Valeurs actuelles
            disabled_fields: Champs desactives
            result: Dictionnaire ou stocker les valeurs
        """
        cols = st.columns(num_columns)
        for i, field in enumerate(fields):
            with cols[i % num_columns]:
                value = self._render_widget(
                    field,
                    key_prefix,
                    current_values.get(field.name),
                    disabled=field.name in disabled_fields or not field.editable,
                )
                result[field.name] = value

    def validate(
        self,
        values: Dict[str, Any],
        exclude_fields: Optional[Set[str]] = None,
    ) -> tuple[bool, List[str]]:
        """Valide les valeurs du formulaire.

        DEPRECATED: Cette methode n'est plus utilisee par DialogGenerator.
        La validation est maintenant centralisee dans Pandera via
        src.validation.integration.validate_for_crud().

        Conservee pour compatibilite ou usage standalone si necessaire.
        Exemple d'usage direct:
            gen = FormGenerator(OPERATION_SCHEMA)
            is_valid, errors = gen.validate(form_data)

        Args:
            values: Valeurs a valider
            exclude_fields: Champs a exclure de la validation

        Returns:
            Tuple (is_valid, liste des messages d'erreur)
        """
        errors = []
        exclude_fields = exclude_fields or set()

        for field in self.schema.fields:
            if field.name in exclude_fields:
                continue
            value = values.get(field.name)

            # Verification requis
            if field.required:
                if value is None or value == "":
                    errors.append(f"Le champ '{field.label}' est requis")
                    continue

            # Validation min/max pour nombres
            if value is not None and value != "":
                if field.min_value is not None:
                    try:
                        if float(value) < float(field.min_value):
                            errors.append(
                                f"'{field.label}' doit etre >= {field.min_value}"
                            )
                    except (TypeError, ValueError):
                        pass

                if field.max_value is not None:
                    try:
                        if float(value) > float(field.max_value):
                            errors.append(
                                f"'{field.label}' doit etre <= {field.max_value}"
                            )
                    except (TypeError, ValueError):
                        pass

        return (len(errors) == 0, errors)

    def clean_values(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """Nettoie les valeurs pour insertion en base.

        Convertit les chaines vides en None, etc.

        Args:
            values: Valeurs brutes du formulaire

        Returns:
            Valeurs nettoyees
        """
        cleaned = {}

        for field in self.schema.fields:
            if field.name not in values:
                continue

            value = values[field.name]

            # Chaines vides -> None
            if isinstance(value, str) and value.strip() == "":
                value = None

            # Zeros non significatifs -> garder (certains champs acceptent 0)
            # On ne convertit pas automatiquement les 0 en None

            cleaned[field.name] = value

        return cleaned

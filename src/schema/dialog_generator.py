"""Generateur de dialogs CRUD a partir de schemas.

Ce module genere automatiquement les dialogs de creation
et edition Streamlit a partir des definitions de schemas.

Usage:
    from src.schema import DialogGenerator
    from src.schema.schemas import OPERATION_SCHEMA

    gen = DialogGenerator(OPERATION_SCHEMA)

    @st.dialog("Nouvelle operation")
    def show_create():
        gen.create_dialog(user="admin")

    @st.dialog("Modifier operation")
    def show_edit(op_id):
        gen.edit_dialog(op_id, user="admin", can_delete=True)
"""

import streamlit as st
from typing import Any, Callable, Dict, Optional, Set

from src.schema.definitions import EntitySchema
from src.schema.form_generator import FormGenerator
from src.database.connection import get_session
from src.database import crud

# Note: Import de validation fait de manière lazy pour éviter import circulaire


class DialogGenerator:
    """Generateur de dialogs pour CRUD."""

    def __init__(self, schema: EntitySchema):
        """Initialise le generateur avec un schema.

        Args:
            schema: Schema de l'entite
        """
        self.schema = schema
        self.form_gen = FormGenerator(schema)
        self._crud = getattr(crud, schema.crud_instance)

    def _get_entity(self, session, entity_id: int) -> Any:
        """Recupere une entite par son ID.

        Args:
            session: Session SQLAlchemy
            entity_id: ID de l'entite

        Returns:
            Entite ou None
        """
        return self._crud.get(session, entity_id)

    def _extract_values(self, entity: Any) -> Dict[str, Any]:
        """Extrait les valeurs d'une entite.

        Args:
            entity: Objet SQLAlchemy

        Returns:
            Dictionnaire des valeurs
        """
        values = {}
        for field in self.schema.fields:
            values[field.name] = getattr(entity, field.name, None)
        return values

    def create_dialog(
        self,
        user: str = "anonymous",
        parent_id: Optional[int] = None,
        exclude_fields: Optional[Set[str]] = None,
        initial_values: Optional[Dict[str, Any]] = None,
        on_success: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
    ) -> None:
        """Genere un dialog de creation.

        Args:
            user: Utilisateur pour l'audit
            parent_id: ID du parent (pour entites enfants)
            exclude_fields: Champs a exclure du formulaire
            initial_values: Valeurs initiales pour pre-remplir le formulaire
            on_success: Callback appele apres creation reussie
            on_cancel: Callback appele lors de l'annulation
        """
        exclude_fields = exclude_fields or set()

        with st.form(f"create_{self.schema.name}_form"):
            values = self.form_gen.render_form(
                key_prefix=f"create_{self.schema.name}",
                current_values=initial_values,
                exclude_fields=exclude_fields,
            )

            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button(
                    f"Creer {self.schema.display_name.lower()}",
                    type="primary",
                    use_container_width=True,
                )
            with col2:
                cancelled = st.form_submit_button(
                    "Annuler",
                    use_container_width=True,
                )

        if cancelled:
            if on_cancel:
                on_cancel()
            st.rerun(scope="app")

        if submitted:
            # Validation unique via Pandera (requis, types, min/max, enums)
            from src.validation import validate_for_crud

            pandera_result = validate_for_crud(
                self.schema, values, exclude_fields=exclude_fields
            )

            if not pandera_result.is_valid:
                for error in pandera_result.errors:
                    st.error(error)
                st.stop()  # Arrete le script pour empecher la sauvegarde

            # Afficher les warnings (non bloquants)
            for warning in pandera_result.warnings:
                st.warning(warning)

            try:
                cleaned = self.form_gen.clean_values(values)

                # Ajouter le parent_id si necessaire
                if parent_id and self.schema.parent_fk_field:
                    cleaned[self.schema.parent_fk_field] = parent_id

                with get_session() as session:
                    self._crud.create(session, cleaned, user=user)

                st.toast(
                    f"{self.schema.display_name} cree(e) avec succes!",
                    icon="✅",
                )

                if on_success:
                    on_success()

                st.rerun()

            except Exception as e:
                st.error(f"Erreur lors de la creation: {e}")

    def edit_dialog(
        self,
        entity_id: int,
        user: str = "anonymous",
        can_delete: bool = False,
        exclude_fields: Optional[Set[str]] = None,
        disabled_fields: Optional[Set[str]] = None,
        on_success: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
    ) -> None:
        """Genere un dialog d'edition.

        Args:
            entity_id: ID de l'entite a editer
            user: Utilisateur pour l'audit
            can_delete: Autoriser la suppression
            exclude_fields: Champs a exclure du formulaire
            disabled_fields: Champs en lecture seule
            on_success: Callback appele apres mise a jour reussie
            on_delete: Callback appele apres suppression reussie
            on_cancel: Callback appele lors de l'annulation
        """
        exclude_fields = exclude_fields or set()
        disabled_fields = disabled_fields or set()

        # Toujours desactiver l'ID primaire
        disabled_fields = disabled_fields | {self.schema.primary_key}

        # Recuperer l'entite
        with get_session() as session:
            entity = self._get_entity(session, entity_id)

        if not entity:
            st.error(f"{self.schema.display_name} #{entity_id} non trouve(e)")
            if st.button("Fermer"):
                st.rerun()
            return

        # Extraire les valeurs actuelles
        current_values = self._extract_values(entity)

        with st.form(f"edit_{self.schema.name}_form"):
            values = self.form_gen.render_form(
                key_prefix=f"edit_{self.schema.name}",
                current_values=current_values,
                exclude_fields=exclude_fields,
                disabled_fields=disabled_fields,
            )

            # Boutons
            if can_delete:
                col1, col2, col3 = st.columns(3)
            else:
                col1, col2 = st.columns(2)
                col3 = None

            with col1:
                save_btn = st.form_submit_button(
                    "Enregistrer",
                    type="primary",
                    use_container_width=True,
                )
            with col2:
                cancel_btn = st.form_submit_button(
                    "Annuler",
                    use_container_width=True,
                )
            if col3:
                with col3:
                    delete_btn = st.form_submit_button(
                        "Supprimer",
                        use_container_width=True,
                    )
            else:
                delete_btn = False

        if cancel_btn:
            if on_cancel:
                on_cancel()
            st.rerun(scope="app")

        if save_btn:
            # Validation unique via Pandera (requis, types, min/max, enums)
            from src.validation import validate_for_crud

            pandera_result = validate_for_crud(
                self.schema, values, exclude_fields=exclude_fields
            )

            if not pandera_result.is_valid:
                for error in pandera_result.errors:
                    st.error(error)
                st.stop()  # Arrete le script pour empecher la sauvegarde

            # Afficher les warnings (non bloquants)
            for warning in pandera_result.warnings:
                st.warning(warning)

            try:
                cleaned = self.form_gen.clean_values(values)

                # Retirer les champs non modifiables
                for field_name in disabled_fields:
                    cleaned.pop(field_name, None)

                with get_session() as session:
                    obj = self._get_entity(session, entity_id)
                    if obj:
                        self._crud.update(session, obj, cleaned, user=user)

                st.toast(
                    f"{self.schema.display_name} mis(e) a jour!",
                    icon="✅",
                )

                if on_success:
                    on_success()

                st.rerun()

            except Exception as e:
                st.error(f"Erreur lors de la mise a jour: {e}")

        if delete_btn:
            self._handle_delete(entity_id, user, on_delete)

    def _handle_delete(
        self,
        entity_id: int,
        user: str,
        on_delete: Optional[Callable] = None,
    ) -> None:
        """Gere la suppression d'une entite.

        Args:
            entity_id: ID de l'entite
            user: Utilisateur pour l'audit
            on_delete: Callback apres suppression
        """
        try:
            with get_session() as session:
                self._crud.delete(session, entity_id, user=user)

            st.toast(
                f"{self.schema.display_name} supprime(e)!",
                icon="🗑️",
            )

            if on_delete:
                on_delete()

            st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de la suppression: {e}")

    def render_detail(
        self,
        entity_id: int,
        exclude_fields: Optional[Set[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Affiche les details d'une entite en lecture seule.

        Args:
            entity_id: ID de l'entite
            exclude_fields: Champs a exclure

        Returns:
            Dictionnaire des valeurs ou None
        """
        exclude_fields = exclude_fields or {"created_at", "updated_at"}

        with get_session() as session:
            entity = self._get_entity(session, entity_id)

        if not entity:
            st.error(f"{self.schema.display_name} #{entity_id} non trouve(e)")
            return None

        values = self._extract_values(entity)

        # Afficher par section
        for section in self.schema.get_sections_ordered():
            section_fields = self.schema.get_fields_by_section(section.name)
            section_fields = [f for f in section_fields if f.name not in exclude_fields]

            if not section_fields:
                continue

            if section.collapsible:
                with st.expander(section.label, expanded=section.expanded):
                    self._render_detail_section(section_fields, values, section.columns)
            else:
                st.markdown(f"**{section.label}**")
                self._render_detail_section(section_fields, values, section.columns)

        return values

    def _render_detail_section(
        self,
        fields: list,
        values: Dict[str, Any],
        num_columns: int,
    ) -> None:
        """Affiche une section en mode detail.

        Args:
            fields: Champs de la section
            values: Valeurs de l'entite
            num_columns: Nombre de colonnes
        """
        cols = st.columns(num_columns)
        for i, field in enumerate(fields):
            with cols[i % num_columns]:
                value = values.get(field.name)
                display_value = value if value is not None else "-"

                # Formatter si necessaire
                if field.formatter and value is not None:
                    display_value = field.formatter(value)

                st.metric(label=field.label, value=display_value)

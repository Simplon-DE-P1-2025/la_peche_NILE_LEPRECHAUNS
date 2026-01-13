"""Generateur de listes/DataFrames a partir de schemas.

Ce module genere automatiquement les DataFrames et listes
Streamlit a partir des definitions de schemas.

Usage:
    from src.schema import ListGenerator
    from src.schema.schemas import OPERATION_SCHEMA

    gen = ListGenerator(OPERATION_SCHEMA)
    df = gen.build_dataframe(operations)
    selected_id = gen.render_list(operations, on_select=handle_select)
"""

import pandas as pd
import streamlit as st
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from src.schema.definitions import EntitySchema, FieldSchema


class ListGenerator:
    """Generateur de listes/DataFrames a partir de schemas."""

    def __init__(self, schema: EntitySchema):
        """Initialise le generateur avec un schema.

        Args:
            schema: Schema de l'entite
        """
        self.schema = schema
        self._list_fields = schema.get_list_fields()

    def _format_value(self, value: Any, field: FieldSchema) -> Any:
        """Formate une valeur pour affichage.

        Args:
            value: Valeur brute
            field: Definition du champ

        Returns:
            Valeur formatee pour affichage
        """
        if value is None:
            return "-"

        # Utiliser le formatter custom si disponible
        if field.formatter:
            return field.formatter(value)

        # Formatage par defaut selon le type
        if isinstance(value, Decimal):
            if field.format_str:
                return field.format_str % float(value)
            return float(value)

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")

        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")

        return value

    def build_dataframe(
        self,
        objects: List[Any],
        include_id: bool = True,
    ) -> pd.DataFrame:
        """Construit un DataFrame a partir d'objets SQLAlchemy.

        Args:
            objects: Liste d'objets du modele
            include_id: Inclure la colonne ID (meme si non visible)

        Returns:
            DataFrame pret pour affichage
        """
        data = []

        for obj in objects:
            row = {}

            # Toujours inclure l'ID pour la selection
            if include_id:
                pk_field = self.schema.get_field(self.schema.primary_key)
                if pk_field:
                    raw_id = getattr(obj, self.schema.primary_key, None)
                    row["ID"] = raw_id

            # Ajouter les champs visibles
            for field in self._list_fields:
                # Eviter de dupliquer l'ID si deja inclus
                if include_id and field.name == self.schema.primary_key:
                    continue

                raw_value = getattr(obj, field.name, None)
                row[field.label] = self._format_value(raw_value, field)

            data.append(row)

        return pd.DataFrame(data)

    def get_column_config(self) -> Dict[str, Any]:
        """Retourne la configuration des colonnes pour st.dataframe.

        Returns:
            Configuration des colonnes
        """
        config = {}

        for field in self._list_fields:
            col_config = {}

            if field.list_width:
                col_config["width"] = field.list_width

            if col_config:
                config[field.label] = st.column_config.Column(**col_config)

        return config

    def render_list(
        self,
        objects: List[Any],
        on_select: Optional[Callable[[int], None]] = None,
        key: str = "entity_list",
        use_container_width: bool = True,
        height: Optional[int] = None,
    ) -> Optional[int]:
        """Affiche la liste avec selection.

        Args:
            objects: Liste d'objets a afficher
            on_select: Callback appele lors d'une selection
            key: Cle Streamlit pour le widget
            use_container_width: Utiliser toute la largeur
            height: Hauteur en pixels

        Returns:
            ID de l'element selectionne ou None
        """
        if not objects:
            st.info(f"Aucun(e) {self.schema.display_name.lower()} trouve(e)")
            return None

        df = self.build_dataframe(objects, include_id=True)

        # Configuration de l'affichage
        display_config = {
            "use_container_width": use_container_width,
            "hide_index": True,
            "column_config": self.get_column_config(),
            "key": key,
        }

        if height:
            display_config["height"] = height

        # Mode selection si callback fourni
        if on_select:
            display_config["on_select"] = "rerun"
            display_config["selection_mode"] = "single-row"

            event = st.dataframe(df, **display_config)

            if event.selection and event.selection.rows:
                selected_idx = event.selection.rows[0]
                # Retrouver l'ID depuis le DataFrame
                selected_id = df.iloc[selected_idx]["ID"]
                on_select(int(selected_id))
                return int(selected_id)
        else:
            st.dataframe(df, **display_config)

        return None

    def render_simple_table(
        self,
        objects: List[Any],
        max_rows: int = 10,
    ) -> None:
        """Affiche une table simple sans selection.

        Args:
            objects: Liste d'objets a afficher
            max_rows: Nombre maximum de lignes
        """
        if not objects:
            st.info(f"Aucun(e) {self.schema.display_name.lower()}")
            return

        df = self.build_dataframe(objects[:max_rows], include_id=False)
        st.table(df)

        if len(objects) > max_rows:
            st.caption(f"... et {len(objects) - max_rows} de plus")

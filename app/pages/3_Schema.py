"""Page Schema de la base de donnees - Version dynamique.

Cette page affiche:
- Le diagramme ER genere dynamiquement depuis les FK de la base
- La description des tables lues depuis information_schema
- Les index lus depuis pg_indexes

L'approche "data-driven" garantit que la documentation reste
synchronisee avec le schema reel de la base de donnees.

Date: Janvier 2026
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# =============================================================================
# Configuration du path pour imports
# =============================================================================
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.database.raw_queries import (
    get_all_tables,
    get_table_schema,
    get_foreign_keys,
    get_primary_keys,
    get_table_indexes,
    generate_mermaid_er,
)


# =============================================================================
# Configuration de la page Streamlit
# =============================================================================
st.set_page_config(page_title="Schema BDD SECMAR", page_icon="📐", layout="wide")


# =============================================================================
# Authentification
# =============================================================================
if not login_required():
    st.stop()

show_user_info()


# =============================================================================
# En-tete de la page
# =============================================================================
st.title("📐 Schema de la Base de Donnees")
st.caption("Architecture et relations des tables SECMAR - Genere dynamiquement")


# =============================================================================
# Section: Architecture hybride
# =============================================================================
st.subheader("🏗️ Architecture Hybride")

st.markdown(
    """
Cette application utilise une **approche hybride** combinant :

| Composant | Technologie | Usage |
|-----------|-------------|-------|
| **CRUD** | SQLAlchemy ORM | Operations unitaires, relations |
| **Analytics** | Raw SQL (psycopg2) | Requetes complexes, agregations |
| **Bulk Load** | execute_values | Chargement massif ETL |
| **Audit** | Triggers PostgreSQL | Capture automatique des modifications |
"""
)

st.divider()


# =============================================================================
# Section: Diagramme ER dynamique
# =============================================================================
st.subheader("📊 Diagramme Entite-Relation - limité à 8 colonnes pour la lisibilité")

# Generer le code Mermaid depuis les FK de la base
try:
    mermaid_code = generate_mermaid_er()

    # Essayer d'utiliser streamlit-mermaid si disponible
    try:
        from streamlit_mermaid import st_mermaid

        st_mermaid(mermaid_code, height=600)
    except ImportError:
        # Fallback: afficher le code Mermaid brut
        st.warning(
            "Le module `streamlit-mermaid` n'est pas installe. "
            "Affichage du code Mermaid genere."
        )
        st.code(mermaid_code, language="mermaid")

    # Bouton pour voir le code source
    with st.expander("📝 Voir le code Mermaid genere"):
        st.code(mermaid_code, language="mermaid")
        st.caption("Ce code est genere automatiquement depuis les FK de la base")

except Exception as e:
    st.error(f"Erreur lors de la generation du diagramme: {e}")
    st.info("Verifiez que la connexion a la base de donnees est etablie.")

st.divider()


# =============================================================================
# Section: Description des tables (dynamique)
# =============================================================================
st.subheader("📋 Description des tables")

# Recuperer la liste des tables
tables = get_all_tables()

if not tables:
    st.warning("Aucune table trouvee dans le schema public.")
else:
    st.caption(f"{len(tables)} tables dans le schema public")

    # Recuperer les FK pour afficher les relations
    foreign_keys = get_foreign_keys()

    # Creer un dictionnaire des FK par table
    fk_by_table = {}
    for fk in foreign_keys:
        table = fk["table_name"]
        if table not in fk_by_table:
            fk_by_table[table] = []
        fk_by_table[table].append(fk)

    # Creer un set des colonnes FK par table pour marquage rapide
    fk_columns = {}
    for fk in foreign_keys:
        table = fk["table_name"]
        if table not in fk_columns:
            fk_columns[table] = set()
        fk_columns[table].add(fk["column_name"])

    # Recuperer les PK et creer un mapping par table
    primary_keys = get_primary_keys()
    pk_by_table = {pk["table_name"]: pk["column_name"] for pk in primary_keys}

    # Afficher chaque table dans un expander
    for table in tables:
        # Recuperer le schema de la table
        schema = get_table_schema(table)

        if not schema:
            continue

        # Determiner si c'est une table principale
        is_main = table in [
            "operations",
            "flotteurs",
            "resultats_humain",
            "operations_stats",
        ]
        expanded = is_main

        with st.expander(f"**{table}**", expanded=expanded):
            # Creer un DataFrame pour l'affichage
            data = []
            for col in schema:
                # Formater le type de donnees
                data_type = col["data_type"].upper()
                if col.get("character_maximum_length"):
                    data_type = f"VARCHAR({col['character_maximum_length']})"
                elif col.get("numeric_precision"):
                    data_type = f"{data_type}({col['numeric_precision']})"

                # Determiner les contraintes
                constraints = []

                # Marquer PK en premier
                if pk_by_table.get(table) == col["column_name"]:
                    constraints.append("🔑 PK")

                # Marquer FK
                if col["column_name"] in fk_columns.get(table, set()):
                    constraints.append("🔗 FK")

                if col["is_nullable"] == "NO":
                    constraints.append("NOT NULL")
                if col.get("column_default"):
                    if "nextval" in str(col["column_default"]):
                        constraints.append("SERIAL")
                    elif "now()" in str(col["column_default"]):
                        constraints.append("DEFAULT NOW()")

                data.append(
                    {
                        "Colonne": col["column_name"],
                        "Type": data_type,
                        "Nullable": "Oui" if col["is_nullable"] == "YES" else "Non",
                        "Contraintes": ", ".join(constraints) if constraints else "-",
                    }
                )

            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Afficher les relations FK
            if table in fk_by_table:
                st.markdown("**Relations:**")
                for fk in fk_by_table[table]:
                    st.markdown(
                        f"- `{fk['column_name']}` → "
                        f"`{fk['foreign_table_name']}.{fk['foreign_column_name']}`"
                    )

st.divider()


# =============================================================================
# Section: Systeme d'audit
# =============================================================================
st.subheader("🔍 Systeme d'audit")

st.markdown(
    """
L'audit est gere par des **triggers PostgreSQL** qui capturent automatiquement
toutes les modifications sur les tables principales.
"""
)

st.code(
    """
-- Exemple de trigger
CREATE TRIGGER audit_operations
    AFTER INSERT OR UPDATE OR DELETE ON operations
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- La fonction audit_trigger_func() :
-- 1. Capture OLD et NEW values en JSONB
-- 2. Identifie les champs modifies
-- 3. Log l'utilisateur via current_setting('app.current_user')
-- 4. Insere dans audit_log
""",
    language="sql",
)

st.info(
    """
**Avantage des triggers** : L'audit capture TOUTES les modifications,
meme celles faites directement en SQL (pas uniquement via l'application).
"""
)

st.divider()


# =============================================================================
# Section: Index de performance (dynamique)
# =============================================================================
st.subheader("⚡ Index de performance")

# Recuperer les index depuis pg_indexes
indexes = get_table_indexes()

if indexes:
    # Filtrer les index non-PK (les PK ont des noms comme table_pkey)
    filtered_indexes = [
        idx for idx in indexes if not idx["indexname"].endswith("_pkey")
    ]

    if filtered_indexes:
        # Creer un DataFrame
        data = []
        for idx in filtered_indexes:
            data.append(
                {
                    "Table": idx["tablename"],
                    "Index": idx["indexname"],
                    "Definition": (
                        idx["indexdef"].split(" USING ")[-1]
                        if " USING " in idx["indexdef"]
                        else "-"
                    ),
                }
            )

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun index secondaire trouve (hors cles primaires)")
else:
    st.info("Aucun index trouve dans la base")


# =============================================================================
# Section: Statistiques de la base
# =============================================================================
st.divider()
st.subheader("📈 Statistiques de la base")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Tables", len(tables) if tables else 0)

with col2:
    st.metric("Relations FK", len(foreign_keys) if foreign_keys else 0)

with col3:
    # Compter les index non-PK
    secondary_indexes = (
        len([i for i in indexes if not i["indexname"].endswith("_pkey")])
        if indexes
        else 0
    )
    st.metric("Index secondaires", secondary_indexes)

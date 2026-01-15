"""Page d'audit - Historique des modifications.

Cette page affiche le journal d'audit avec:
- Statistiques globales (insertions, mises a jour, suppressions)
- Filtres par table, type d'operation, utilisateur et date
- Detail des modifications avec diff avant/apres
- Export CSV des logs

L'audit est alimente par des triggers PostgreSQL, ce qui garantit
la capture de TOUTES les modifications (meme hors application).

Date: Janvier 2026
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

# =============================================================================
# Configuration du path pour imports
# =============================================================================
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auth.authentificator import login_required, show_user_info
from src.database.raw_queries import get_audit_logs, get_audit_stats, get_audited_tables

# =============================================================================
# Configuration de la page Streamlit
# =============================================================================
st.set_page_config(page_title="Audit SECMAR", page_icon="📋", layout="wide")


# =============================================================================
# Authentification
# =============================================================================
if not login_required():
    st.stop()

show_user_info()


# =============================================================================
# En-tete de la page
# =============================================================================
st.title("📋 Journal d'Audit")
st.caption("Historique des modifications de la base de donnees")

# =============================================================================
# Statistiques
# =============================================================================
stats = get_audit_stats()

if stats and stats.get("total_entries", 0) > 0:
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total entrées", f"{stats.get('total_entries', 0):,}".replace(",", " ")
        )

    with col2:
        st.metric("🟢 Insertions", stats.get("total_inserts", 0))

    with col3:
        st.metric("🟡 Mises à jour", stats.get("total_updates", 0))

    with col4:
        st.metric("🔴 Suppressions", stats.get("total_deletes", 0))

    with col5:
        st.metric("Utilisateurs", stats.get("users_active", 0))

st.divider()

# =============================================================================
# Section: Filtres
# =============================================================================
st.subheader("🔍 Filtres")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Liste des tables dynamique depuis audit_log, avec fallback
    audited_tables = get_audited_tables()
    if not audited_tables:
        # Fallback si audit_log est vide
        audited_tables = [
            "operations",
            "flotteurs",
            "resultats_humain",
            "operations_stats",
        ]

    filter_table = st.selectbox(
        "Table", options=["Toutes"] + audited_tables, key="audit_table"
    )
    filter_table = None if filter_table == "Toutes" else filter_table

with col2:
    filter_operation = st.selectbox(
        "Type d'opération",
        options=["Toutes", "INSERT", "UPDATE", "DELETE"],
        key="audit_op",
    )
    filter_operation = None if filter_operation == "Toutes" else filter_operation

with col3:
    filter_user = st.text_input("Utilisateur", key="audit_user")
    filter_user = filter_user if filter_user else None

with col4:
    filter_date = st.date_input(
        "Depuis", value=datetime.now() - timedelta(days=7), key="audit_date"
    )

limit = st.slider("Nombre d'entrées", min_value=50, max_value=1000, value=200, step=50)

# =============================================================================
# Section: Donnees d'audit
# =============================================================================
st.subheader("📝 Entrees d'audit")

results = get_audit_logs(
    table_name=filter_table,
    operation_type=filter_operation,
    user_id=filter_user,
    date_debut=filter_date,
    limit=limit,
)

st.caption(f"Affichage de {len(results)} entrées")

if results:
    # Préparer les données pour l'affichage
    data = []
    for r in results:
        # Emoji selon le type d'opération
        emoji = {"INSERT": "🟢", "UPDATE": "🟡", "DELETE": "🔴"}.get(
            r.get("operation_type"), "⚪"
        )

        # Formater le timestamp
        ts = r.get("timestamp")
        if ts:
            if isinstance(ts, str):
                ts_str = ts[:19]
            else:
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = "-"

        data.append(
            {
                "Date/Heure": ts_str,
                "Table": r.get("table_name", "-"),
                "Action": f"{emoji} {r.get('operation_type', '-')}",
                "ID Record": r.get("record_id", "-"),
                "Utilisateur": r.get("user_id", "system"),
                "Champs modifiés": ", ".join(r.get("changed_fields") or []) or "-",
            }
        )

    df = pd.DataFrame(data)

    # Afficher avec sélection
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # Détail si sélectionné
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_entry = results[selected_idx]

        st.markdown("---")
        st.subheader("🔎 Détail de l'entrée")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Anciennes valeurs")
            old_values = selected_entry.get("old_values")
            if old_values:
                if isinstance(old_values, str):
                    old_values = json.loads(old_values)
                st.json(old_values)
            else:
                st.info("N/A (nouvelle entrée)")

        with col2:
            st.markdown("#### Nouvelles valeurs")
            new_values = selected_entry.get("new_values")
            if new_values:
                if isinstance(new_values, str):
                    new_values = json.loads(new_values)
                st.json(new_values)
            else:
                st.info("N/A (suppression)")

        # Diff pour les UPDATE
        if selected_entry.get("operation_type") == "UPDATE":
            changed_fields = selected_entry.get("changed_fields") or []
            if changed_fields:
                st.markdown("#### Modifications")

                diff_data = []
                old_vals = selected_entry.get("old_values") or {}
                new_vals = selected_entry.get("new_values") or {}

                if isinstance(old_vals, str):
                    old_vals = json.loads(old_vals)
                if isinstance(new_vals, str):
                    new_vals = json.loads(new_vals)

                for field in changed_fields:
                    diff_data.append(
                        {
                            "Champ": field,
                            "Avant": str(old_vals.get(field, "-")),
                            "Après": str(new_vals.get(field, "-")),
                        }
                    )

                st.dataframe(pd.DataFrame(diff_data), hide_index=True)

else:
    st.info("Aucune entrée d'audit trouvée avec ces filtres")

# =============================================================================
# Section: Export des logs
# =============================================================================
st.divider()

with st.expander("📥 Exporter les logs"):
    if results:
        # Préparer pour export
        export_data = []
        for r in results:
            export_data.append(
                {
                    "id": r.get("id"),
                    "timestamp": str(r.get("timestamp")),
                    "table_name": r.get("table_name"),
                    "operation_type": r.get("operation_type"),
                    "record_id": r.get("record_id"),
                    "user_id": r.get("user_id"),
                    "changed_fields": ", ".join(r.get("changed_fields") or []),
                    "old_values": (
                        json.dumps(r.get("old_values")) if r.get("old_values") else ""
                    ),
                    "new_values": (
                        json.dumps(r.get("new_values")) if r.get("new_values") else ""
                    ),
                }
            )

        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False)

        st.download_button(
            label="Télécharger en CSV",
            data=csv,
            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Pas de données à exporter")

# =============================================================================
# Section: A propos de l'audit
# =============================================================================
st.divider()

with st.expander("ℹ️ A propos de l'audit"):
    st.markdown(
        """
    ### Comment fonctionne l'audit ?

    L'audit est géré par des **triggers PostgreSQL** qui s'exécutent automatiquement
    lors de chaque modification (INSERT, UPDATE, DELETE) sur les tables :

    - `operations`
    - `flotteurs`
    - `resultats_humain`
    - `operations_stats`

    ### Informations capturées

    | Champ | Description |
    |-------|-------------|
    | `table_name` | Table modifiée |
    | `operation_type` | INSERT, UPDATE ou DELETE |
    | `record_id` | ID de l'enregistrement concerné |
    | `old_values` | Valeurs AVANT modification (JSONB) |
    | `new_values` | Valeurs APRÈS modification (JSONB) |
    | `changed_fields` | Liste des champs modifiés (UPDATE) |
    | `user_id` | Utilisateur ayant fait la modification |
    | `timestamp` | Date et heure |

    ### Avantages des triggers

    - ✅ Capture **toutes** les modifications, même directes en SQL
    - ✅ Aucun code à maintenir côté application
    - ✅ Performance optimale
    - ✅ Impossible à contourner
    """
    )

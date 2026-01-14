"""Requêtes analytiques en Raw SQL - Approche Hybride.

Ces requêtes sont trop complexes ou trop lourdes pour l'ORM,
on utilise du SQL direct pour de meilleures performances.

Usage:
    from src.database.raw_queries import get_kpis, get_operations_by_cross

    kpis = get_kpis()
    print(f"Total opérations: {kpis['total_operations']}")

    by_cross = get_operations_by_cross()
    for row in by_cross:
        print(f"{row['cross']}: {row['total_operations']}")
"""

from datetime import date
from typing import Optional
import pandas as pd

from src.database.connection import execute_raw_sql


# =============================================================================
# KPIs généraux
# =============================================================================


def get_kpis() -> dict:
    """Récupérer les KPIs principaux du dashboard.

    Returns:
        Dictionnaire avec les KPIs globaux
    """
    sql = """
    SELECT
        COUNT(*) as total_operations,
        COUNT(DISTINCT o."cross") as nb_cross,
        COUNT(DISTINCT o.departement) as nb_departements,
        COALESCE(SUM(s.nombre_impliques), 0) as total_personnes,
        MIN(o.date_heure_reception_alerte) as premiere_operation,
        MAX(o.date_heure_reception_alerte) as derniere_operation
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE o.date_heure_reception_alerte IS NOT NULL
    """
    result = execute_raw_sql(sql)
    return result[0] if result else {}


def get_kpis_by_period(
    date_debut: Optional[date] = None, date_fin: Optional[date] = None
) -> dict:
    """KPIs pour une période donnée.

    Args:
        date_debut: Date de début (optionnel)
        date_fin: Date de fin (optionnel)

    Returns:
        Dictionnaire avec les KPIs de la période
    """
    sql = """
    SELECT
        COUNT(*) as total_operations,
        COALESCE(SUM(s.nombre_impliques), 0) as total_personnes,
        COUNT(DISTINCT o."cross") as nb_cross
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE 1=1
        AND (:date_debut IS NULL OR o.date_heure_reception_alerte >= :date_debut)
        AND (:date_fin IS NULL OR o.date_heure_reception_alerte <= :date_fin)
    """
    params = {"date_debut": date_debut, "date_fin": date_fin}
    result = execute_raw_sql(sql, params)
    return result[0] if result else {}


# =============================================================================
# Statistiques par dimension
# =============================================================================


def get_operations_by_cross() -> list[dict]:
    """Nombre d'opérations par CROSS.

    Returns:
        Liste de dictionnaires {cross, total_operations, total_personnes}
    """
    sql = """
    SELECT
        COALESCE(o."cross", 'Non renseigné') as cross,
        COUNT(*) as total_operations,
        COALESCE(SUM(s.nombre_impliques), 0) as total_personnes
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    GROUP BY COALESCE(o."cross", 'Non renseigné')
    ORDER BY total_operations DESC
    """
    return execute_raw_sql(sql)


def get_operations_by_type() -> list[dict]:
    """Répartition par type d'opération.

    Returns:
        Liste de dictionnaires {type_operation, total, pourcentage}
    """
    sql = """
    SELECT
        COALESCE(type_operation, 'Autre') as type_operation,
        COUNT(*) as total,
        ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER(), 0), 2) as pourcentage
    FROM operations
    GROUP BY COALESCE(type_operation, 'Autre')
    ORDER BY total DESC
    """
    return execute_raw_sql(sql)


def get_operations_by_department(limit: int = 20) -> list[dict]:
    """Opérations par département.

    Args:
        limit: Nombre maximum de départements à retourner

    Returns:
        Liste de dictionnaires {departement, total_operations, total_personnes}
    """
    sql = """
    SELECT
        o.departement,
        COUNT(*) as total_operations,
        COALESCE(SUM(s.nombre_impliques), 0) as total_personnes
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE o.departement IS NOT NULL
    GROUP BY o.departement
    ORDER BY total_operations DESC
    LIMIT :limit
    """
    return execute_raw_sql(sql, {"limit": limit})


def get_cross_list() -> list[str]:
    """Récupérer la liste des CROSS distincts.

    Returns:
        Liste des noms de CROSS
    """
    sql = """
    SELECT DISTINCT "cross"
    FROM operations
    WHERE "cross" IS NOT NULL
    ORDER BY "cross"
    """
    results = execute_raw_sql(sql)
    return [r["cross"] for r in results]


def get_type_list() -> list[str]:
    """Récupérer la liste des types d'opération distincts.

    Returns:
        Liste des types
    """
    sql = """
    SELECT DISTINCT type_operation
    FROM operations
    WHERE type_operation IS NOT NULL
    ORDER BY type_operation
    """
    results = execute_raw_sql(sql)
    return [r["type_operation"] for r in results]


# =============================================================================
# Évolution temporelle
# =============================================================================


def get_operations_timeline(
    granularity: str = "month",
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
) -> list[dict]:
    """Évolution du nombre d'opérations dans le temps.

    Args:
        granularity: 'day', 'week', 'month', 'year'
        date_debut: Date de début (optionnel)
        date_fin: Date de fin (optionnel)

    Returns:
        Liste de dictionnaires {periode, total_operations, total_personnes}
    """
    date_trunc = {"day": "day", "week": "week", "month": "month", "year": "year"}.get(
        granularity, "month"
    )

    sql = f"""
    SELECT
        DATE_TRUNC('{date_trunc}', o.date_heure_reception_alerte) as periode,
        COUNT(*) as total_operations,
        COALESCE(SUM(s.nombre_impliques), 0) as total_personnes
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE o.date_heure_reception_alerte IS NOT NULL
        AND (:date_debut IS NULL OR o.date_heure_reception_alerte >= :date_debut)
        AND (:date_fin IS NULL OR o.date_heure_reception_alerte <= :date_fin)
    GROUP BY DATE_TRUNC('{date_trunc}', o.date_heure_reception_alerte)
    ORDER BY periode
    """
    return execute_raw_sql(sql, {"date_debut": date_debut, "date_fin": date_fin})


def get_monthly_comparison() -> list[dict]:
    """Comparaison mois par mois sur plusieurs années.

    Returns:
        Liste de dictionnaires {annee, mois, total_operations}
    """
    sql = """
    SELECT
        EXTRACT(YEAR FROM date_heure_reception_alerte)::int as annee,
        EXTRACT(MONTH FROM date_heure_reception_alerte)::int as mois,
        COUNT(*) as total_operations
    FROM operations
    WHERE date_heure_reception_alerte IS NOT NULL
    GROUP BY annee, mois
    ORDER BY annee, mois
    """
    return execute_raw_sql(sql)


def get_yearly_stats() -> list[dict]:
    """Statistiques annuelles.

    Returns:
        Liste de dictionnaires avec stats par année
    """
    sql = """
    SELECT
        EXTRACT(YEAR FROM o.date_heure_reception_alerte)::int as annee,
        COUNT(*) as total_operations,
        COALESCE(SUM(s.nombre_impliques), 0) as total_personnes
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE o.date_heure_reception_alerte IS NOT NULL
    GROUP BY annee
    ORDER BY annee DESC
    """
    return execute_raw_sql(sql)


# =============================================================================
# Bilan humain
# =============================================================================


def get_bilan_humain_global() -> dict:
    """Bilan humain global.

    Returns:
        Dictionnaire avec totaux (décédés, disparus, blessés, sauvés, etc.)
    """
    sql = """
    SELECT
        COALESCE(SUM(nombre_decedes), 0) as total_decedes,
        COALESCE(SUM(nombre_disparus), 0) as total_disparus,
        COALESCE(SUM(nombre_blesses), 0) as total_blesses,
        COALESCE(SUM(nombre_sauves), 0) as total_sauves,
        COALESCE(SUM(nombre_impliques), 0) as total_impliques,
        COALESCE(SUM(nombre_assistances), 0) as total_assistances
    FROM operations_stats
    """
    result = execute_raw_sql(sql)
    return result[0] if result else {}


def get_bilan_by_cross() -> list[dict]:
    """Bilan humain par CROSS.

    Returns:
        Liste de dictionnaires {cross, decedes, disparus, blesses, sauves}
    """
    sql = """
    SELECT
        COALESCE(o."cross", 'Non renseigné') as cross,
        COALESCE(SUM(s.nombre_decedes), 0) as decedes,
        COALESCE(SUM(s.nombre_disparus), 0) as disparus,
        COALESCE(SUM(s.nombre_blesses), 0) as blesses,
        COALESCE(SUM(s.nombre_sauves), 0) as sauves
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    GROUP BY COALESCE(o."cross", 'Non renseigné')
    ORDER BY sauves DESC
    """
    return execute_raw_sql(sql)


def get_bilan_by_cross_filtered(
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None
) -> list[dict]:
    """Bilan humain par CROSS avec filtres de date.

    Args:
        date_debut: Date de début (optionnel)
        date_fin: Date de fin (optionnel)

    Returns:
        Liste de dictionnaires {cross, decedes, disparus, blesses, sauves}
    """
    sql = """
    SELECT
        COALESCE(o."cross", 'Non renseigné') as cross,
        COALESCE(SUM(s.nombre_decedes), 0) as decedes,
        COALESCE(SUM(s.nombre_disparus), 0) as disparus,
        COALESCE(SUM(s.nombre_blesses), 0) as blesses,
        COALESCE(SUM(s.nombre_sauves), 0) as sauves
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE 1=1
        AND (:date_debut IS NULL OR o.date_heure_reception_alerte >= :date_debut)
        AND (:date_fin IS NULL OR o.date_heure_reception_alerte <= :date_fin)
    GROUP BY COALESCE(o."cross", 'Non renseigné')
    ORDER BY sauves DESC
    """
    return execute_raw_sql(sql, {"date_debut": date_debut, "date_fin": date_fin})


def get_bilan_by_period(
    date_debut: Optional[date] = None, date_fin: Optional[date] = None
) -> dict:
    """Bilan humain pour une période.

    Args:
        date_debut: Date de début
        date_fin: Date de fin

    Returns:
        Dictionnaire avec le bilan de la période
    """
    sql = """
    SELECT
        COALESCE(SUM(s.nombre_decedes), 0) as total_decedes,
        COALESCE(SUM(s.nombre_disparus), 0) as total_disparus,
        COALESCE(SUM(s.nombre_blesses), 0) as total_blesses,
        COALESCE(SUM(s.nombre_sauves), 0) as total_sauves,
        COALESCE(SUM(s.nombre_impliques), 0) as total_impliques,
        COALESCE(SUM(s.nombre_assistances), 0) as total_assistances
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE 1=1
        AND (:date_debut IS NULL OR o.date_heure_reception_alerte >= :date_debut)
        AND (:date_fin IS NULL OR o.date_heure_reception_alerte <= :date_fin)
    """
    result = execute_raw_sql(sql, {"date_debut": date_debut, "date_fin": date_fin})
    return result[0] if result else {}


def get_resultats_humain_stats() -> list[dict]:
    """Statistiques détaillées des résultats humains.

    Returns:
        Liste de dictionnaires {resultat, categorie, total}
    """
    sql = """
    SELECT
        COALESCE(resultat_humain, 'Inconnu') as resultat,
        COALESCE(categorie_personne, 'Autre') as categorie,
        COALESCE(SUM(nombre), 0) as total
    FROM resultats_humain
    GROUP BY resultat_humain, categorie_personne
    ORDER BY total DESC
    """
    return execute_raw_sql(sql)


# =============================================================================
# Analyse des flotteurs
# =============================================================================


def get_flotteurs_stats(limit: int = 15) -> list[dict]:
    """Statistiques sur les types de flotteurs.

    Args:
        limit: Nombre maximum de types à retourner

    Returns:
        Liste de dictionnaires {type_flotteur, total, categorie_flotteur}
    """
    sql = """
    SELECT
        COALESCE(type_flotteur, 'Non renseigné') as type_flotteur,
        COALESCE(categorie_flotteur, 'Non renseigné') as categorie_flotteur,
        COUNT(*) as total
    FROM flotteurs
    GROUP BY COALESCE(type_flotteur, 'Non renseigné'), COALESCE(categorie_flotteur, 'Non renseigné')
    ORDER BY total DESC
    LIMIT :limit
    """
    return execute_raw_sql(sql, {"limit": limit})


def get_flotteurs_by_pavillon(limit: int = 10) -> list[dict]:
    """Répartition des flotteurs par pavillon.

    Args:
        limit: Nombre maximum de pavillons

    Returns:
        Liste de dictionnaires {pavillon, total, pourcentage}
    """
    sql = """
    SELECT
        COALESCE(pavillon, 'Inconnu') as pavillon,
        COUNT(*) as total,
        ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER(), 0), 2) as pourcentage
    FROM flotteurs
    GROUP BY COALESCE(pavillon, 'Inconnu')
    ORDER BY total DESC
    LIMIT :limit
    """
    return execute_raw_sql(sql, {"limit": limit})


# =============================================================================
# Requêtes complexes
# =============================================================================


def get_top_operations_by_personnes(limit: int = 10) -> list[dict]:
    """Top des opérations avec le plus de personnes impliquées.

    Args:
        limit: Nombre d'opérations à retourner

    Returns:
        Liste des opérations les plus importantes
    """
    sql = """
    WITH ranked_ops AS (
        SELECT
            o.operation_id,
            o.date_heure_reception_alerte,
            o.type_operation,
            o."cross",
            COALESCE(s.nombre_impliques, 0) as nombre_impliques,
            COALESCE(s.nombre_sauves, 0) as nombre_sauves,
            ROW_NUMBER() OVER (ORDER BY COALESCE(s.nombre_impliques, 0) DESC) as rang
        FROM operations o
        LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
        WHERE s.nombre_impliques > 0
    )
    SELECT * FROM ranked_ops WHERE rang <= :limit
    """
    return execute_raw_sql(sql, {"limit": limit})


def get_operations_with_casualties() -> list[dict]:
    """Opérations avec victimes (décédés ou disparus).

    Returns:
        Liste des opérations avec victimes, triées par gravité
    """
    sql = """
    SELECT
        o.operation_id,
        o.date_heure_reception_alerte,
        o.type_operation,
        o."cross",
        o.departement,
        s.nombre_decedes,
        s.nombre_disparus,
        (COALESCE(s.nombre_decedes, 0) + COALESCE(s.nombre_disparus, 0)) as total_victimes
    FROM operations o
    INNER JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE s.nombre_decedes > 0 OR s.nombre_disparus > 0
    ORDER BY total_victimes DESC, o.date_heure_reception_alerte DESC
    LIMIT 50
    """
    return execute_raw_sql(sql)


def search_operations_advanced(
    cross: str = None,
    type_operation: str = None,
    departement: str = None,
    date_debut: date = None,
    date_fin: date = None,
    min_personnes: int = None,
    has_casualties: bool = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Recherche avancée d'opérations avec tous les filtres.

    Args:
        cross: Filtrer par CROSS
        type_operation: Filtrer par type
        departement: Filtrer par département
        date_debut: Date minimum
        date_fin: Date maximum
        min_personnes: Minimum de personnes impliquées (via operations_stats)
        has_casualties: Si True, uniquement les opérations avec victimes
        limit: Nombre maximum de résultats
        offset: Décalage pour pagination

    Returns:
        Liste des opérations correspondantes
    """
    sql = """
    SELECT
        o.operation_id,
        o.date_heure_reception_alerte,
        o.type_operation,
        o."cross",
        o.departement,
        COALESCE(s.nombre_impliques, 0) as nombre_impliques,
        COALESCE(s.nombre_sauves, 0) as nombre_sauves,
        COALESCE(s.nombre_decedes, 0) as nombre_decedes,
        COALESCE(s.nombre_disparus, 0) as nombre_disparus
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE 1=1
        AND (:cross IS NULL OR o."cross" = :cross)
        AND (:type_operation IS NULL OR o.type_operation = :type_operation)
        AND (:departement IS NULL OR o.departement = :departement)
        AND (:date_debut IS NULL OR o.date_heure_reception_alerte >= :date_debut)
        AND (:date_fin IS NULL OR o.date_heure_reception_alerte <= :date_fin)
        AND (:min_personnes IS NULL OR COALESCE(s.nombre_impliques, 0) >= :min_personnes)
        AND (:has_casualties IS NULL OR
             (:has_casualties = true AND (s.nombre_decedes > 0 OR s.nombre_disparus > 0)) OR
             (:has_casualties = false AND COALESCE(s.nombre_decedes, 0) = 0 AND COALESCE(s.nombre_disparus, 0) = 0))
    ORDER BY o.date_heure_reception_alerte DESC
    LIMIT :limit OFFSET :offset
    """
    return execute_raw_sql(
        sql,
        {
            "cross": cross,
            "type_operation": type_operation,
            "departement": departement,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "min_personnes": min_personnes,
            "has_casualties": has_casualties,
            "limit": limit,
            "offset": offset,
        },
    )


# =============================================================================
# Export vers DataFrame
# =============================================================================


def query_to_dataframe(sql: str, params: dict = None) -> pd.DataFrame:
    """Exécuter une requête et retourner un DataFrame.

    Args:
        sql: Requête SQL
        params: Paramètres de la requête

    Returns:
        DataFrame pandas
    """
    results = execute_raw_sql(sql, params)
    return pd.DataFrame(results) if results else pd.DataFrame()


def get_operations_dataframe(
    cross: str = None,
    date_debut: date = None,
    date_fin: date = None,
    limit: int = 10000,
) -> pd.DataFrame:
    """Export des opérations en DataFrame avec filtres.

    Args:
        cross: Filtrer par CROSS
        date_debut: Date minimum
        date_fin: Date maximum
        limit: Nombre maximum de lignes

    Returns:
        DataFrame avec les opérations
    """
    sql = """
    SELECT
        o.operation_id,
        o.date_heure_reception_alerte,
        o.type_operation,
        o.sous_type_operation,
        o."cross",
        o.departement,
        o.latitude,
        o.longitude,
        COALESCE(s.nombre_impliques, 0) as nombre_impliques,
        COALESCE(s.nombre_sauves, 0) as nombre_sauves,
        COALESCE(s.nombre_decedes, 0) as nombre_decedes,
        COALESCE(s.nombre_disparus, 0) as nombre_disparus,
        COALESCE(s.nombre_blesses, 0) as nombre_blesses
    FROM operations o
    LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
    WHERE 1=1
        AND (:cross IS NULL OR o."cross" = :cross)
        AND (:date_debut IS NULL OR o.date_heure_reception_alerte >= :date_debut)
        AND (:date_fin IS NULL OR o.date_heure_reception_alerte <= :date_fin)
    ORDER BY o.date_heure_reception_alerte DESC
    LIMIT :limit
    """
    return query_to_dataframe(
        sql,
        {
            "cross": cross,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "limit": limit,
        },
    )


# =============================================================================
# Audit
# =============================================================================


def get_audit_logs(
    table_name: str = None,
    operation_type: str = None,
    user_id: str = None,
    date_debut: date = None,
    limit: int = 500,
) -> list[dict]:
    """Récupérer les logs d'audit.

    Args:
        table_name: Filtrer par table
        operation_type: Filtrer par type (INSERT, UPDATE, DELETE)
        user_id: Filtrer par utilisateur
        date_debut: Date minimum
        limit: Nombre maximum de logs

    Returns:
        Liste des entrées d'audit
    """
    sql = """
    SELECT
        id,
        table_name,
        operation_type,
        record_id,
        old_values,
        new_values,
        changed_fields,
        user_id,
        timestamp
    FROM audit_log
    WHERE 1=1
        AND (:table_name IS NULL OR table_name = :table_name)
        AND (:operation_type IS NULL OR operation_type = :operation_type)
        AND (:user_id IS NULL OR user_id ILIKE '%' || :user_id || '%')
        AND (:date_debut IS NULL OR timestamp >= :date_debut)
    ORDER BY timestamp DESC
    LIMIT :limit
    """
    return execute_raw_sql(
        sql,
        {
            "table_name": table_name,
            "operation_type": operation_type,
            "user_id": user_id,
            "date_debut": date_debut,
            "limit": limit,
        },
    )


def get_audit_stats() -> dict:
    """Statistiques sur l'audit.

    Returns:
        Dictionnaire avec stats d'audit
    """
    sql = """
    SELECT
        COUNT(*) as total_entries,
        COUNT(DISTINCT table_name) as tables_tracked,
        COUNT(DISTINCT user_id) as users_active,
        SUM(CASE WHEN operation_type = 'INSERT' THEN 1 ELSE 0 END) as total_inserts,
        SUM(CASE WHEN operation_type = 'UPDATE' THEN 1 ELSE 0 END) as total_updates,
        SUM(CASE WHEN operation_type = 'DELETE' THEN 1 ELSE 0 END) as total_deletes,
        MIN(timestamp) as first_entry,
        MAX(timestamp) as last_entry
    FROM audit_log
    """
    result = execute_raw_sql(sql)
    return result[0] if result else {}


# =============================================================================
# Schema et metadonnees (pour page Schema dynamique)
# =============================================================================


def get_all_tables() -> list[str]:
    """Liste des tables du schema clean.

    Returns:
        Liste des noms de tables
    """
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'clean'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    results = execute_raw_sql(sql)
    return [r["table_name"] for r in results]


def get_table_schema(table_name: str) -> list[dict]:
    """Recuperer le schema d'une table depuis information_schema.

    Args:
        table_name: Nom de la table

    Returns:
        Liste de dictionnaires avec infos colonnes
    """
    sql = """
    SELECT
        column_name,
        data_type,
        character_maximum_length,
        numeric_precision,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = 'clean'
      AND table_name = :table_name
    ORDER BY ordinal_position
    """
    return execute_raw_sql(sql, {"table_name": table_name})


def get_primary_keys() -> list[dict]:
    """Recuperer les cles primaires de toutes les tables.

    Returns:
        Liste de dictionnaires {table_name, column_name}
    """
    sql = """
    SELECT
        tc.table_name,
        kcu.column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema = 'clean'
    ORDER BY tc.table_name
    """
    return execute_raw_sql(sql)


def get_foreign_keys() -> list[dict]:
    """Recuperer les relations FK pour generer le diagramme ER.

    Returns:
        Liste de dictionnaires avec infos FK
    """
    sql = """
    SELECT
        tc.table_name,
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name,
        tc.constraint_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'clean'
    ORDER BY tc.table_name
    """
    return execute_raw_sql(sql)


def get_table_indexes(table_name: str = None) -> list[dict]:
    """Recuperer les index d'une table ou de toutes les tables.

    Args:
        table_name: Nom de la table (optionnel, None = toutes)

    Returns:
        Liste de dictionnaires avec infos index
    """
    sql = """
    SELECT
        tablename,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname = 'clean'
      AND (:table_name IS NULL OR tablename = :table_name)
    ORDER BY tablename, indexname
    """
    return execute_raw_sql(sql, {"table_name": table_name})


def get_audited_tables() -> list[str]:
    """Recuperer la liste des tables presentes dans audit_log.

    Returns:
        Liste des noms de tables auditees
    """
    sql = """
    SELECT DISTINCT table_name
    FROM audit_log
    ORDER BY table_name
    """
    results = execute_raw_sql(sql)
    return [r["table_name"] for r in results] if results else []


def generate_mermaid_er() -> str:
    """Generer le code Mermaid ER depuis les FK de la base.

    Returns:
        Code Mermaid pour diagramme ER
    """
    fks = get_foreign_keys()
    tables = get_all_tables()
    pks = get_primary_keys()

    # Creer un mapping des PK par table
    pk_map = {}
    for pk in pks:
        pk_map[pk["table_name"]] = pk["column_name"]

    # Mapping des types SQL vers types Mermaid simples (sans espaces)
    type_mapping = {
        "character varying": "string",
        "varchar": "string",
        "text": "string",
        "integer": "int",
        "bigint": "bigint",
        "smallint": "smallint",
        "serial": "serial",
        "numeric": "decimal",
        "decimal": "decimal",
        "real": "float",
        "double precision": "double",
        "boolean": "boolean",
        "date": "date",
        "time": "time",
        "time without time zone": "time",
        "timestamp": "timestamp",
        "timestamp without time zone": "timestamp",
        "timestamp with time zone": "timestamptz",
        "jsonb": "jsonb",
        "json": "json",
        "array": "array",
        "user-defined": "custom",
    }

    # Debut du diagramme
    lines = ["erDiagram"]

    # Ajouter les relations (sans doublons)
    seen_relations = set()
    for fk in fks:
        relation_key = (fk["foreign_table_name"], fk["table_name"])
        if relation_key not in seen_relations:
            seen_relations.add(relation_key)
            lines.append(
                f'    {fk["foreign_table_name"]} ||--o{{ {fk["table_name"]} : contient'
            )

    # Ajouter les entites avec leurs colonnes principales
    for table in tables:
        schema = get_table_schema(table)
        if schema:
            lines.append("")
            lines.append(f"    {table} {{")

            for col in schema[:8]:  # Limiter a 8 colonnes pour lisibilite
                # Convertir le type SQL en type Mermaid simple
                raw_type = col["data_type"].lower()
                mermaid_type = type_mapping.get(raw_type, "string")

                # Marqueurs PK/FK
                pk_marker = " PK" if col["column_name"] == pk_map.get(table) else ""
                fk_marker = ""
                for fk in fks:
                    if fk["table_name"] == table and fk["column_name"] == col["column_name"]:
                        fk_marker = " FK"
                        break

                lines.append(f'        {mermaid_type} {col["column_name"]}{pk_marker}{fk_marker}')

            lines.append("    }")

    return "\n".join(lines)

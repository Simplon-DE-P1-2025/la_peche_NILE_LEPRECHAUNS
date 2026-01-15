"""Requêtes KPI Analytics avancées - Basées sur les vues SQL.

Ce module fournit des fonctions pour accéder aux KPIs calculés par les vues SQL
définies dans sql/views_kpi.sql.

Vues utilisées:
- v_kpi_securite_mensuel    : Taux de sécurité par mois
- v_kpi_cross_benchmark     : Performance et ranking des CROSS
- v_kpi_flotteurs_analyse   : Statistiques par type de flotteur
- v_kpi_temporel_multidim   : Analyse temporelle multi-dimensions
- v_kpi_meteo_correlation   : Corrélations météo/gravité
- v_kpi_yoy_comparison      : Comparatifs année sur année
- v_kpi_alertes_anomalies   : Détection d'anomalies (z-scores)
- v_kpi_geographique        : Analyse par zone géographique
- v_kpi_type_operation      : Stats par type d'opération

Usage:
    from src.database.kpi_queries import (
        get_kpi_securite_mensuel,
        get_kpi_cross_benchmark,
        get_kpi_yoy_comparison,
    )

    # KPIs de sécurité (définition officielle SECMAR)
    securite = get_kpi_securite_mensuel(annee=2024)
    print(f"Taux saines et sauves: {securite[0]['taux_saines_sauves']}%")

    # Benchmarking CROSS
    benchmark = get_kpi_cross_benchmark()
    for cross in benchmark:
        print(f"{cross['cross_name']}: Rank #{cross['rank_sauvetage']}")
"""

from datetime import date
from typing import Optional
import pandas as pd

from src.database.connection import execute_raw_sql


# =============================================================================
# Liste des CROSS actuellement actifs (importée de raw_queries)
# =============================================================================
CROSS_ACTIFS = [
    "Antilles-Guyane",
    "Corse",
    "Corsen",
    "Étel",
    "Etel",  # Variante sans accent
    "Gris-Nez",
    "Jobourg",
    "La Garde",
    "Nouvelle-Calédonie",
    "Polynésie",
    "Sud océan Indien",
]


def _build_cross_filter(alias: str = "o") -> tuple[str, dict]:
    """Construit la clause WHERE et les paramètres pour filtrer par CROSS actifs.

    Args:
        alias: Alias de la table operations (défaut: 'o')

    Returns:
        Tuple (clause_sql, params_dict)
    """
    placeholders = ", ".join([f":cross_{i}" for i in range(len(CROSS_ACTIFS))])
    params = {f"cross_{i}": cross for i, cross in enumerate(CROSS_ACTIFS)}
    return f'{alias}."cross" IN ({placeholders})', params


def _build_cross_name_filter() -> tuple[str, dict]:
    """Construit la clause WHERE pour filtrer par cross_name (vues avec CROSS).

    Returns:
        Tuple (clause_sql, params_dict)
    """
    placeholders = ", ".join([f":cross_{i}" for i in range(len(CROSS_ACTIFS))])
    params = {f"cross_{i}": cross for i, cross in enumerate(CROSS_ACTIFS)}
    return f"cross_name IN ({placeholders})", params


# =============================================================================
# KPIs de Sécurité Maritime
# =============================================================================

def get_kpi_securite_mensuel(
    annee: Optional[int] = None,
    mois: Optional[int] = None,
    limit: int = 24,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les KPIs de sécurité mensuels.

    Indicateurs inclus:
    - Taux de sauvetage, mortalité, disparition, blessure
    - Indice de gravité composite
    - Totaux par catégorie (décédés, disparus, sauvés, blessés)

    Args:
        annee: Filtrer par année (optionnel)
        mois: Filtrer par mois (optionnel)
        limit: Nombre max de périodes à retourner (défaut: 24 mois)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec les KPIs par période mensuelle
    """
    params = {"annee": annee, "mois": mois, "limit": limit}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            DATE_TRUNC('month', o.date_heure_reception_alerte)::DATE AS periode,
            EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
            EXTRACT(MONTH FROM o.date_heure_reception_alerte)::INTEGER AS mois,
            COUNT(*)::INTEGER AS nb_operations,
            COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
            COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
            ROUND(
                COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_saines_sauves,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_impliques,
            COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
            COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
            COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
            ROUND(
                COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_mortalite,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
                 COALESCE(SUM(os.nombre_disparus), 0) * 2 +
                 COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) AS indice_gravite
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.date_heure_reception_alerte IS NOT NULL
            AND {cross_clause}
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
            AND (:mois IS NULL OR EXTRACT(MONTH FROM o.date_heure_reception_alerte) = :mois)
        GROUP BY DATE_TRUNC('month', o.date_heure_reception_alerte),
                 EXTRACT(YEAR FROM o.date_heure_reception_alerte),
                 EXTRACT(MONTH FROM o.date_heure_reception_alerte)
        ORDER BY periode DESC
        LIMIT :limit
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_securite_mensuel
        WHERE 1=1
            AND (:annee IS NULL OR annee = :annee)
            AND (:mois IS NULL OR mois = :mois)
        ORDER BY periode DESC
        LIMIT :limit
        """
    return execute_raw_sql(sql, params)


def get_kpi_securite_global(
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    cross_actifs_seulement: bool = False,
) -> dict:
    """Récupérer les KPIs de sécurité globaux (agrégation totale).

    Args:
        date_debut: Date de début (optionnel)
        date_fin: Date de fin (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Dictionnaire avec les KPIs agrégés sur la période
    """
    params = {"date_debut": date_debut, "date_fin": date_fin}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            COUNT(*) as total_operations,
            COALESCE(SUM(os.nombre_impliques), 0) as total_impliques,
            COALESCE(SUM(os.nombre_decedes), 0) as total_decedes,
            COALESCE(SUM(os.nombre_disparus), 0) as total_disparus,
            COALESCE(SUM(os.nombre_saines_sauves), 0) as total_saines_sauves,
            COALESCE(SUM(os.nombre_prises_en_compte), 0) as total_prises_en_compte,
            COALESCE(SUM(os.nombre_blesses), 0) as total_blesses,
            ROUND(COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC / NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) as taux_mortalite,
            ROUND(COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC / NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 + COALESCE(SUM(os.nombre_disparus), 0) * 2 + COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) as indice_gravite
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.date_heure_reception_alerte IS NOT NULL
            AND {cross_clause}
            AND (:date_debut IS NULL OR o.date_heure_reception_alerte >= :date_debut)
            AND (:date_fin IS NULL OR o.date_heure_reception_alerte <= :date_fin)
        """
    else:
        sql = """
        SELECT
            SUM(nb_operations) as total_operations,
            SUM(total_impliques) as total_impliques,
            SUM(total_decedes) as total_decedes,
            SUM(total_disparus) as total_disparus,
            SUM(total_saines_sauves) as total_saines_sauves,
            SUM(total_prises_en_compte) as total_prises_en_compte,
            SUM(total_blesses) as total_blesses,
            ROUND(SUM(total_decedes)::NUMERIC / NULLIF(SUM(total_prises_en_compte), 0) * 100, 2) as taux_mortalite,
            ROUND(SUM(total_saines_sauves)::NUMERIC / NULLIF(SUM(total_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
            ROUND(
                (SUM(total_decedes) * 3 + SUM(total_disparus) * 2 + SUM(total_blesses))::NUMERIC /
                NULLIF(SUM(total_prises_en_compte), 0), 3
            ) as indice_gravite
        FROM v_kpi_securite_mensuel
        WHERE 1=1
            AND (:date_debut IS NULL OR periode >= :date_debut)
            AND (:date_fin IS NULL OR periode <= :date_fin)
        """
    result = execute_raw_sql(sql, params)
    return result[0] if result else {}


def get_kpi_lives_saved(
    annee: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> dict:
    """Récupérer le KPI "Saines et Sauves" (définition officielle SECMAR).

    Ce KPI représente le nombre total de personnes mises hors de danger,
    selon la définition du Programme 205 (Budget de l'État).

    Args:
        annee: Année spécifique (optionnel, sinon total cumulé)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Dictionnaire avec saines_sauves et métadonnées
    """
    params = {"annee": annee}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            COALESCE(CAST(:annee AS TEXT), 'CUMUL') as periode,
            COALESCE(SUM(os.nombre_saines_sauves), 0) as saines_sauves,
            COALESCE(SUM(os.nombre_prises_en_compte), 0) as prises_en_compte,
            COUNT(*) as total_operations,
            ROUND(COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC / NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) as taux_saines_sauves
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.date_heure_reception_alerte IS NOT NULL
            AND {cross_clause}
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
        """
    else:
        sql = """
        SELECT
            COALESCE(CAST(:annee AS TEXT), 'CUMUL') as periode,
            SUM(total_saines_sauves) as saines_sauves,
            SUM(total_prises_en_compte) as prises_en_compte,
            SUM(nb_operations) as total_operations,
            ROUND(SUM(total_saines_sauves)::NUMERIC / NULLIF(SUM(total_prises_en_compte), 0) * 100, 2) as taux_saines_sauves
        FROM v_kpi_securite_mensuel
        WHERE (:annee IS NULL OR annee = :annee)
        """
    result = execute_raw_sql(sql, params)
    return result[0] if result else {}


# =============================================================================
# KPIs Performance CROSS (Benchmarking)
# =============================================================================

def get_kpi_cross_benchmark(
    cross_filter: Optional[str] = None,
    top_n: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer le benchmark de performance des CROSS.

    Métriques incluses:
    - Durées d'intervention (moyenne, médiane, min, max)
    - Taux de sauvetage et mortalité
    - Charge de travail (ops/jour)
    - Rankings (volume, sauvetage, rapidité)

    Args:
        cross_filter: Filtrer par nom de CROSS (optionnel)
        top_n: Limiter au top N CROSS par volume (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec les métriques par CROSS
    """
    params = {"cross_filter": cross_filter}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_name_filter()
        params.update(cross_params)
        sql = f"""
        SELECT *
        FROM v_kpi_cross_benchmark
        WHERE (:cross_filter IS NULL OR cross_name = :cross_filter)
            AND {cross_clause}
        ORDER BY nb_operations DESC
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_cross_benchmark
        WHERE (:cross_filter IS NULL OR cross_name = :cross_filter)
        ORDER BY nb_operations DESC
        """

    if top_n:
        sql += f" LIMIT {top_n}"

    return execute_raw_sql(sql, params)


def get_kpi_cross_detail(
    cross_name: str,
    cross_actifs_seulement: bool = False,
) -> dict:
    """Récupérer les détails de performance d'un CROSS spécifique.

    Args:
        cross_name: Nom du CROSS
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Dictionnaire avec toutes les métriques du CROSS
    """
    params = {"cross_name": cross_name}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_name_filter()
        params.update(cross_params)
        sql = f"""
        SELECT *
        FROM v_kpi_cross_benchmark
        WHERE cross_name = :cross_name AND {cross_clause}
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_cross_benchmark
        WHERE cross_name = :cross_name
        """
    result = execute_raw_sql(sql, params)
    return result[0] if result else {}


def get_kpi_cross_ranking(
    metric: str = "sauvetage",
    cross_filter: Optional[str] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer le ranking des CROSS selon une métrique.

    Args:
        metric: Métrique de ranking ('sauvetage', 'volume', 'rapidite')
        cross_filter: Filtrer sur un CROSS spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste des CROSS triés par le ranking demandé
    """
    order_col = {
        "sauvetage": "rank_sauvetage",
        "volume": "rank_volume",
        "rapidite": "rank_rapidite"
    }.get(metric, "rank_sauvetage")

    params: dict = {"cross_filter": cross_filter}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_name_filter()
        params.update(cross_params)
        sql = f"""
        SELECT cross_name, nb_operations, taux_saines_sauves, duree_mediane_heures,
               rank_volume, rank_sauvetage, rank_rapidite
        FROM v_kpi_cross_benchmark
        WHERE {cross_clause}
            AND (:cross_filter IS NULL OR cross_name = :cross_filter)
        ORDER BY {order_col} ASC
        """
    else:
        sql = f"""
        SELECT cross_name, nb_operations, taux_saines_sauves, duree_mediane_heures,
               rank_volume, rank_sauvetage, rank_rapidite
        FROM v_kpi_cross_benchmark
        WHERE (:cross_filter IS NULL OR cross_name = :cross_filter)
        ORDER BY {order_col} ASC
        """
    return execute_raw_sql(sql, params)


# =============================================================================
# KPIs Flotteurs (Analyse sectorielle)
# =============================================================================

def get_kpi_flotteurs_analyse(
    categorie: Optional[str] = None,
    type_flotteur: Optional[str] = None,
    limit: int = 50,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer l'analyse par type de flotteur.

    Args:
        categorie: Filtrer par catégorie (Pêche, Plaisance, etc.)
        type_flotteur: Filtrer par type spécifique
        limit: Nombre max de résultats
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec les stats par flotteur
    """
    params = {"categorie": categorie, "type_flotteur": type_flotteur, "limit": limit}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            f.type_flotteur,
            f.categorie_flotteur,
            f.resultat_flotteur,
            COUNT(DISTINCT f.operation_id)::INTEGER AS nb_operations,
            COUNT(*)::INTEGER AS nb_flotteurs,
            COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
            COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
            COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
            ROUND(AVG(o.distance_cote_metres)::NUMERIC, 0) AS distance_cote_moyenne_m,
            ROUND(
                COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_saines_sauves,
            ROUND(
                COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_mortalite
        FROM flotteurs f
        JOIN operations o ON f.operation_id = o.operation_id
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE {cross_clause}
            AND (:categorie IS NULL OR f.categorie_flotteur = :categorie)
            AND (:type_flotteur IS NULL OR f.type_flotteur = :type_flotteur)
        GROUP BY f.type_flotteur, f.categorie_flotteur, f.resultat_flotteur
        ORDER BY nb_operations DESC
        LIMIT :limit
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_flotteurs_analyse
        WHERE 1=1
            AND (:categorie IS NULL OR categorie_flotteur = :categorie)
            AND (:type_flotteur IS NULL OR type_flotteur = :type_flotteur)
        ORDER BY nb_operations DESC
        LIMIT :limit
        """
    return execute_raw_sql(sql, params)


def get_kpi_flotteurs_par_categorie(
    categorie: Optional[str] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les statistiques agrégées par catégorie de flotteur.

    Args:
        categorie: Filtrer par catégorie spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec stats par catégorie
    """
    params: dict = {"categorie": categorie}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            f.categorie_flotteur,
            COUNT(DISTINCT f.operation_id)::INTEGER AS total_operations,
            COUNT(*)::INTEGER AS total_flotteurs,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
            COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
            COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
            ROUND(COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC / NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) as taux_mortalite,
            ROUND(COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC / NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
            ROUND(AVG(o.distance_cote_metres), 0) as distance_cote_moyenne_m
        FROM flotteurs f
        JOIN operations o ON f.operation_id = o.operation_id
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE f.categorie_flotteur IS NOT NULL
            AND {cross_clause}
            AND (:categorie IS NULL OR f.categorie_flotteur = :categorie)
        GROUP BY f.categorie_flotteur
        ORDER BY total_operations DESC
        """
    else:
        sql = """
        SELECT
            categorie_flotteur,
            SUM(nb_operations) as total_operations,
            SUM(nb_flotteurs) as total_flotteurs,
            SUM(total_personnes) as total_personnes,
            SUM(total_decedes) as total_decedes,
            SUM(total_saines_sauves) as total_saines_sauves,
            SUM(total_prises_en_compte) as total_prises_en_compte,
            ROUND(SUM(total_decedes)::NUMERIC / NULLIF(SUM(total_prises_en_compte), 0) * 100, 2) as taux_mortalite,
            ROUND(SUM(total_saines_sauves)::NUMERIC / NULLIF(SUM(total_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
            ROUND(AVG(distance_cote_moyenne_m), 0) as distance_cote_moyenne_m
        FROM v_kpi_flotteurs_analyse
        WHERE categorie_flotteur IS NOT NULL
            AND (:categorie IS NULL OR categorie_flotteur = :categorie)
        GROUP BY categorie_flotteur
        ORDER BY total_operations DESC
        """
    return execute_raw_sql(sql, params)


def get_kpi_flotteurs_sports_nautiques(
    categorie: Optional[str] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les stats des sports nautiques émergents.

    Focus sur: Kitesurf, Wingfoil, Kayak, Planche à voile, Jet-ski

    Args:
        categorie: Filtrer par catégorie spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec stats des sports nautiques
    """
    params: dict = {"categorie": categorie}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            f.type_flotteur,
            f.categorie_flotteur,
            COUNT(DISTINCT f.operation_id)::INTEGER AS nb_operations,
            COUNT(*)::INTEGER AS nb_flotteurs,
            COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
            COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
            ROUND(
                COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_mortalite
        FROM flotteurs f
        JOIN operations o ON f.operation_id = o.operation_id
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE f.type_flotteur IN (
            'Kitesurf', 'Canoe/Kayak', 'Planche a voile', 'Jet-ski',
            'Ski nautique', 'Engin de plage'
        )
            AND {cross_clause}
            AND (:categorie IS NULL OR f.categorie_flotteur = :categorie)
        GROUP BY f.type_flotteur, f.categorie_flotteur
        ORDER BY nb_operations DESC
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_flotteurs_analyse
        WHERE type_flotteur IN (
            'Kitesurf', 'Canoe/Kayak', 'Planche a voile', 'Jet-ski',
            'Ski nautique', 'Engin de plage'
        )
            AND (:categorie IS NULL OR categorie_flotteur = :categorie)
        ORDER BY nb_operations DESC
        """
    return execute_raw_sql(sql, params)


# =============================================================================
# KPIs Temporels et Saisonnalité
# =============================================================================

def get_kpi_temporel_multidim(
    annee: Optional[int] = None,
    phase_journee: Optional[str] = None,
    est_vacances: Optional[bool] = None,
    est_ferie: Optional[bool] = None
) -> list[dict]:
    """Récupérer l'analyse temporelle multi-dimensions.

    Args:
        annee: Filtrer par année
        phase_journee: Filtrer par phase (Nuit, Matin, Après-midi, etc.)
        est_vacances: Filtrer par vacances scolaires
        est_ferie: Filtrer par jour férié

    Returns:
        Liste de dictionnaires avec analyse temporelle
    """
    sql = """
    SELECT *
    FROM v_kpi_temporel_multidim
    WHERE 1=1
        AND (:annee IS NULL OR annee = :annee)
        AND (:phase_journee IS NULL OR phase_journee = :phase_journee)
        AND (:est_vacances IS NULL OR est_vacances_scolaires = :est_vacances)
        AND (:est_ferie IS NULL OR est_jour_ferie = :est_ferie)
    ORDER BY annee DESC, mois ASC, nb_operations DESC
    """
    params = {
        "annee": annee,
        "phase_journee": phase_journee,
        "est_vacances": est_vacances,
        "est_ferie": est_ferie
    }
    return execute_raw_sql(sql, params)


def get_kpi_saisonnalite_mensuelle(
    annee: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer la saisonnalité mensuelle agrégée.

    Args:
        annee: Année spécifique ou moyenne multi-années
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec stats par mois
    """
    params = {"annee": annee}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            EXTRACT(MONTH FROM o.date_heure_reception_alerte)::INTEGER AS mois,
            COUNT(*)::INTEGER AS total_operations,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
                 COALESCE(SUM(os.nombre_disparus), 0) * 2 +
                 COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) AS indice_gravite_moyen
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.date_heure_reception_alerte IS NOT NULL
            AND {cross_clause}
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
        GROUP BY EXTRACT(MONTH FROM o.date_heure_reception_alerte)
        ORDER BY mois
        """
    else:
        sql = """
        SELECT
            mois,
            SUM(nb_operations) as total_operations,
            SUM(total_personnes) as total_personnes,
            SUM(total_victimes) as total_victimes,
            ROUND(AVG(indice_gravite), 3) as indice_gravite_moyen
        FROM v_kpi_temporel_multidim
        WHERE (:annee IS NULL OR annee = :annee)
        GROUP BY mois
        ORDER BY mois
        """
    return execute_raw_sql(sql, params)


def get_kpi_phase_journee(
    annee: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les statistiques par phase du jour.

    Args:
        annee: Année spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec stats par phase (Nuit, Matin, etc.)
    """
    params = {"annee": annee}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            o.phase_journee,
            COUNT(*)::INTEGER AS total_operations,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
                 COALESCE(SUM(os.nombre_disparus), 0) * 2 +
                 COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) AS indice_gravite_moyen,
            ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER(), 0), 2) as pct_operations
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.phase_journee IS NOT NULL
            AND {cross_clause}
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
        GROUP BY o.phase_journee
        ORDER BY total_operations DESC
        """
    else:
        sql = """
        SELECT
            phase_journee,
            SUM(nb_operations) as total_operations,
            SUM(total_personnes) as total_personnes,
            SUM(total_victimes) as total_victimes,
            ROUND(AVG(indice_gravite), 3) as indice_gravite_moyen,
            ROUND(100.0 * SUM(nb_operations) / NULLIF(SUM(SUM(nb_operations)) OVER(), 0), 2) as pct_operations
        FROM v_kpi_temporel_multidim
        WHERE phase_journee IS NOT NULL
            AND (:annee IS NULL OR annee = :annee)
        GROUP BY phase_journee
        ORDER BY total_operations DESC
        """
    return execute_raw_sql(sql, params)


def get_kpi_impact_vacances(
    annee: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Comparer les KPIs vacances vs hors-vacances.

    Args:
        annee: Année spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste avec comparatif vacances/hors-vacances
    """
    params = {"annee": annee}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            o.est_vacances_scolaires as en_vacances,
            COUNT(*)::INTEGER AS total_operations,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
            ROUND(AVG(os.nombre_impliques)::NUMERIC, 2) as moy_personnes_par_op,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
                 COALESCE(SUM(os.nombre_disparus), 0) * 2 +
                 COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) AS indice_gravite_moyen
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.est_vacances_scolaires IS NOT NULL
            AND {cross_clause}
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
        GROUP BY o.est_vacances_scolaires
        """
    else:
        sql = """
        SELECT
            est_vacances_scolaires as en_vacances,
            SUM(nb_operations) as total_operations,
            SUM(total_personnes) as total_personnes,
            SUM(total_victimes) as total_victimes,
            ROUND(AVG(moy_personnes_par_op), 2) as moy_personnes_par_op,
            ROUND(AVG(indice_gravite), 3) as indice_gravite_moyen
        FROM v_kpi_temporel_multidim
        WHERE est_vacances_scolaires IS NOT NULL
            AND (:annee IS NULL OR annee = :annee)
        GROUP BY est_vacances_scolaires
        """
    return execute_raw_sql(sql, params)


# =============================================================================
# KPIs Météorologiques
# =============================================================================

def get_kpi_meteo_correlation(
    vent_min: Optional[int] = None,
    vent_max: Optional[int] = None,
    mer_min: Optional[int] = None,
    mer_max: Optional[int] = None,
    annee: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les corrélations météo/incidents.

    Args:
        vent_min: Force vent minimum (Beaufort)
        vent_max: Force vent maximum (Beaufort)
        mer_min: État mer minimum (Douglas)
        mer_max: État mer maximum (Douglas)
        annee: Année spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec corrélations météo
    """
    params = {
        "vent_min": vent_min, "vent_max": vent_max,
        "mer_min": mer_min, "mer_max": mer_max,
        "annee": annee
    }

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            o.vent_force,
            o.mer_force,
            COUNT(*)::INTEGER AS nb_operations,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
            ROUND(
                COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_mortalite,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
                 COALESCE(SUM(os.nombre_disparus), 0) * 2 +
                 COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) AS indice_gravite
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE (o.vent_force IS NOT NULL OR o.mer_force IS NOT NULL)
            AND {cross_clause}
            AND (:vent_min IS NULL OR o.vent_force >= :vent_min)
            AND (:vent_max IS NULL OR o.vent_force <= :vent_max)
            AND (:mer_min IS NULL OR o.mer_force >= :mer_min)
            AND (:mer_max IS NULL OR o.mer_force <= :mer_max)
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
        GROUP BY o.vent_force, o.mer_force
        ORDER BY nb_operations DESC
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_meteo_correlation
        WHERE 1=1
            AND (:vent_min IS NULL OR vent_force >= :vent_min)
            AND (:vent_max IS NULL OR vent_force <= :vent_max)
            AND (:mer_min IS NULL OR mer_force >= :mer_min)
            AND (:mer_max IS NULL OR mer_force <= :mer_max)
        ORDER BY nb_operations DESC
        """
    return execute_raw_sql(sql, params)


def get_kpi_meteo_par_force_vent(
    annee: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les statistiques par force de vent (Beaufort).

    Args:
        annee: Année spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec stats par force de vent
    """
    params = {"annee": annee}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            o.vent_force,
            COUNT(*)::INTEGER AS total_operations,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
            ROUND(
                COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_mortalite_moyen,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
                 COALESCE(SUM(os.nombre_disparus), 0) * 2 +
                 COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) AS indice_gravite_moyen
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.vent_force IS NOT NULL
            AND {cross_clause}
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
        GROUP BY o.vent_force
        ORDER BY o.vent_force
        """
    else:
        sql = """
        SELECT
            vent_force,
            SUM(nb_operations) as total_operations,
            SUM(total_personnes) as total_personnes,
            SUM(total_victimes) as total_victimes,
            ROUND(AVG(taux_mortalite), 2) as taux_mortalite_moyen,
            ROUND(AVG(indice_gravite), 3) as indice_gravite_moyen
        FROM v_kpi_meteo_correlation
        WHERE vent_force IS NOT NULL
        GROUP BY vent_force
        ORDER BY vent_force
        """
    return execute_raw_sql(sql, params)


def get_kpi_meteo_par_etat_mer(
    annee: Optional[int] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les statistiques par état de la mer (Douglas).

    Args:
        annee: Année spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec stats par état de mer
    """
    params = {"annee": annee}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        SELECT
            o.mer_force,
            COUNT(*)::INTEGER AS total_operations,
            COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
            COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
            ROUND(
                COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
            ) AS taux_mortalite_moyen,
            ROUND(
                (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
                 COALESCE(SUM(os.nombre_disparus), 0) * 2 +
                 COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
                NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
            ) AS indice_gravite_moyen
        FROM operations o
        LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
        WHERE o.mer_force IS NOT NULL
            AND {cross_clause}
            AND (:annee IS NULL OR EXTRACT(YEAR FROM o.date_heure_reception_alerte) = :annee)
        GROUP BY o.mer_force
        ORDER BY o.mer_force
        """
    else:
        sql = """
        SELECT
            mer_force,
            SUM(nb_operations) as total_operations,
            SUM(total_personnes) as total_personnes,
            SUM(total_victimes) as total_victimes,
            ROUND(AVG(taux_mortalite), 2) as taux_mortalite_moyen,
            ROUND(AVG(indice_gravite), 3) as indice_gravite_moyen
        FROM v_kpi_meteo_correlation
        WHERE mer_force IS NOT NULL
        GROUP BY mer_force
        ORDER BY mer_force
        """
    return execute_raw_sql(sql, params)


# =============================================================================
# KPIs Year-over-Year (Comparatifs annuels)
# =============================================================================

def get_kpi_yoy_comparison(
    annee: Optional[int] = None,
    limit: int = 10,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les comparatifs année sur année.

    Args:
        annee: Année de référence (optionnel, pour filtrer les années <= annee)
        limit: Nombre d'années à retourner
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec KPIs et variations YoY
    """
    params = {"limit": limit, "annee": annee}

    if cross_actifs_seulement:
        cross_clause, cross_params = _build_cross_filter()
        params.update(cross_params)
        sql = f"""
        WITH yearly_stats AS (
            SELECT
                EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
                COUNT(*)::INTEGER AS nb_operations,
                COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
                COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
                COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
                COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
                COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus
            FROM operations o
            LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
            WHERE o.date_heure_reception_alerte IS NOT NULL AND {cross_clause}
            GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)
        )
        SELECT
            y.annee,
            y.nb_operations,
            y.total_saines_sauves,
            y.total_prises_en_compte,
            ROUND(y.total_saines_sauves::NUMERIC / NULLIF(y.total_prises_en_compte, 0) * 100, 2) AS taux_saines_sauves,
            y.total_personnes,
            y.total_decedes,
            y.total_disparus,
            ROUND(y.total_decedes::NUMERIC / NULLIF(y.total_prises_en_compte, 0) * 100, 2) AS taux_mortalite,
            LAG(y.nb_operations) OVER (ORDER BY y.annee) AS ops_annee_precedente,
            ROUND(
                (y.nb_operations - LAG(y.nb_operations) OVER (ORDER BY y.annee))::NUMERIC /
                NULLIF(LAG(y.nb_operations) OVER (ORDER BY y.annee), 0) * 100, 2
            ) AS yoy_operations_pct,
            ROUND(
                (y.total_personnes - LAG(y.total_personnes) OVER (ORDER BY y.annee))::NUMERIC /
                NULLIF(LAG(y.total_personnes) OVER (ORDER BY y.annee), 0) * 100, 2
            ) AS yoy_personnes_pct,
            ROUND(
                (y.total_saines_sauves - LAG(y.total_saines_sauves) OVER (ORDER BY y.annee))::NUMERIC /
                NULLIF(LAG(y.total_saines_sauves) OVER (ORDER BY y.annee), 0) * 100, 2
            ) AS yoy_sauves_pct
        FROM yearly_stats y
        WHERE (:annee IS NULL OR y.annee <= :annee)
        ORDER BY y.annee DESC
        LIMIT :limit
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_yoy_comparison
        WHERE (:annee IS NULL OR annee <= :annee)
        ORDER BY annee DESC
        LIMIT :limit
        """
    return execute_raw_sql(sql, params)


def get_kpi_yoy_latest(cross_actifs_seulement: bool = False) -> dict:
    """Récupérer les KPIs de l'année en cours vs année précédente.

    Args:
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Dictionnaire avec KPIs et variations YoY
    """
    results = get_kpi_yoy_comparison(limit=1, cross_actifs_seulement=cross_actifs_seulement)
    return results[0] if results else {}


# =============================================================================
# KPIs Alertes et Anomalies
# =============================================================================

def get_kpi_alertes_anomalies(
    niveau_alerte: Optional[str] = None,
    limit: int = 12,
    annee: Optional[int] = None,
    cross: Optional[str] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer les alertes et anomalies détectées.

    Args:
        niveau_alerte: Filtrer par niveau ('ALERTE', 'ATTENTION', 'NORMAL')
        limit: Nombre de périodes à retourner
        annee: Année spécifique (optionnel)
        cross: Filtrer sur un CROSS spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste de dictionnaires avec alertes et z-scores
    """
    params: dict = {"niveau": niveau_alerte, "limit": limit, "annee": annee, "cross": cross}

    if cross_actifs_seulement or cross:
        # Avec filtrage CROSS, on calcule les z-scores avec moyenne mobile 12 mois
        cross_clauses = []
        if cross_actifs_seulement:
            cross_clause, cross_params = _build_cross_filter()
            cross_clauses.append(cross_clause)
            params.update(cross_params)
        if cross:
            cross_clauses.append('o."cross" = :cross')

        where_cross = " AND ".join(cross_clauses) if cross_clauses else "1=1"

        sql = f"""
        WITH monthly_stats AS (
            SELECT
                DATE_TRUNC('month', o.date_heure_reception_alerte)::DATE AS periode,
                COUNT(*)::INTEGER AS nb_operations,
                COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
                COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
                COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
                COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes
            FROM operations o
            LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
            WHERE o.date_heure_reception_alerte IS NOT NULL
                AND {where_cross}
            GROUP BY DATE_TRUNC('month', o.date_heure_reception_alerte)
        ),
        stats_rolling AS (
            SELECT
                m.periode,
                AVG(m2.nb_operations) AS moy_operations,
                STDDEV(m2.nb_operations) AS std_operations,
                AVG(m2.total_victimes) AS moy_victimes,
                STDDEV(m2.total_victimes) AS std_victimes
            FROM monthly_stats m
            LEFT JOIN monthly_stats m2
                ON m2.periode < m.periode
                AND m2.periode >= m.periode - INTERVAL '12 months'
            GROUP BY m.periode
        )
        SELECT
            m.periode,
            m.nb_operations,
            m.total_personnes,
            m.total_decedes,
            m.total_disparus,
            m.total_victimes,
            ROUND(
                (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0), 2
            ) AS zscore_operations,
            ROUND(
                (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0), 2
            ) AS zscore_victimes,
            CASE
                WHEN (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0) > 2.5 THEN 'ALERTE'
                WHEN (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0) > 1.5 THEN 'ATTENTION'
                ELSE 'NORMAL'
            END AS niveau_alerte_victimes,
            CASE
                WHEN (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0) > 2.5 THEN 'ALERTE'
                WHEN (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0) > 1.5 THEN 'ATTENTION'
                ELSE 'NORMAL'
            END AS niveau_alerte_operations
        FROM monthly_stats m
        LEFT JOIN stats_rolling sr ON m.periode = sr.periode
        WHERE (:annee IS NULL OR EXTRACT(YEAR FROM m.periode) = :annee)
        ORDER BY m.periode DESC
        LIMIT :limit
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_alertes_anomalies
        WHERE (:niveau IS NULL OR niveau_alerte_victimes = :niveau OR niveau_alerte_operations = :niveau)
            AND (:annee IS NULL OR EXTRACT(YEAR FROM periode) = :annee)
        ORDER BY periode DESC
        LIMIT :limit
        """
    return execute_raw_sql(sql, params)


def get_kpi_alertes_actives(
    annee: Optional[int] = None,
    cross: Optional[str] = None,
    cross_actifs_seulement: bool = False,
) -> list[dict]:
    """Récupérer uniquement les périodes en alerte ou attention.

    Args:
        annee: Année spécifique (optionnel)
        cross: Filtrer sur un CROSS spécifique (optionnel)
        cross_actifs_seulement: Si True, filtre uniquement sur les CROSS actifs.

    Returns:
        Liste des périodes avec alertes actives
    """
    params: dict = {"annee": annee, "cross": cross}

    if cross_actifs_seulement or cross:
        # Avec filtrage CROSS, on calcule les z-scores avec moyenne mobile 12 mois
        cross_clauses = []
        if cross_actifs_seulement:
            cross_clause, cross_params = _build_cross_filter()
            cross_clauses.append(cross_clause)
            params.update(cross_params)
        if cross:
            cross_clauses.append('o."cross" = :cross')

        where_cross = " AND ".join(cross_clauses) if cross_clauses else "1=1"

        sql = f"""
        WITH monthly_stats AS (
            SELECT
                DATE_TRUNC('month', o.date_heure_reception_alerte)::DATE AS periode,
                COUNT(*)::INTEGER AS nb_operations,
                COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
                COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
                COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
                COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes
            FROM operations o
            LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
            WHERE o.date_heure_reception_alerte IS NOT NULL
                AND {where_cross}
            GROUP BY DATE_TRUNC('month', o.date_heure_reception_alerte)
        ),
        stats_rolling AS (
            SELECT
                m.periode,
                AVG(m2.nb_operations) AS moy_operations,
                STDDEV(m2.nb_operations) AS std_operations,
                AVG(m2.total_victimes) AS moy_victimes,
                STDDEV(m2.total_victimes) AS std_victimes
            FROM monthly_stats m
            LEFT JOIN monthly_stats m2
                ON m2.periode < m.periode
                AND m2.periode >= m.periode - INTERVAL '12 months'
            GROUP BY m.periode
        )
        SELECT
            m.periode,
            m.nb_operations,
            m.total_personnes,
            m.total_decedes,
            m.total_disparus,
            m.total_victimes,
            ROUND(
                (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0), 2
            ) AS zscore_operations,
            ROUND(
                (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0), 2
            ) AS zscore_victimes,
            CASE
                WHEN (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0) > 2.5 THEN 'ALERTE'
                WHEN (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0) > 1.5 THEN 'ATTENTION'
                ELSE 'NORMAL'
            END AS niveau_alerte_victimes,
            CASE
                WHEN (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0) > 2.5 THEN 'ALERTE'
                WHEN (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0) > 1.5 THEN 'ATTENTION'
                ELSE 'NORMAL'
            END AS niveau_alerte_operations
        FROM monthly_stats m
        LEFT JOIN stats_rolling sr ON m.periode = sr.periode
        WHERE (
            (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0) > 1.5
            OR (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0) > 1.5
        )
            AND (:annee IS NULL OR EXTRACT(YEAR FROM m.periode) = :annee)
        ORDER BY m.periode DESC
        LIMIT 24
        """
    else:
        sql = """
        SELECT *
        FROM v_kpi_alertes_anomalies
        WHERE (niveau_alerte_victimes IN ('ALERTE', 'ATTENTION')
           OR niveau_alerte_operations IN ('ALERTE', 'ATTENTION'))
            AND (:annee IS NULL OR EXTRACT(YEAR FROM periode) = :annee)
        ORDER BY periode DESC
        """
    return execute_raw_sql(sql, params)


# =============================================================================
# KPIs Géographiques
# =============================================================================

def get_kpi_geographique(
    prefecture: Optional[str] = None,
    cross_name: Optional[str] = None,
    departement: Optional[str] = None
) -> list[dict]:
    """Récupérer l'analyse géographique.

    Args:
        prefecture: Filtrer par préfecture maritime
        cross_name: Filtrer par CROSS
        departement: Filtrer par département

    Returns:
        Liste de dictionnaires avec analyse géographique
    """
    sql = """
    SELECT *
    FROM v_kpi_geographique
    WHERE 1=1
        AND (:prefecture IS NULL OR prefecture_maritime = :prefecture)
        AND (:cross_name IS NULL OR cross_name = :cross_name)
        AND (:departement IS NULL OR departement = :departement)
    ORDER BY nb_operations DESC
    """
    params = {
        "prefecture": prefecture,
        "cross_name": cross_name,
        "departement": departement
    }
    return execute_raw_sql(sql, params)


def get_kpi_par_prefecture() -> list[dict]:
    """Récupérer les KPIs agrégés par préfecture maritime.

    Returns:
        Liste de dictionnaires avec stats par préfecture
    """
    sql = """
    SELECT
        prefecture_maritime,
        SUM(nb_operations) as total_operations,
        SUM(total_personnes) as total_personnes,
        SUM(total_saines_sauves) as total_saines_sauves,
        SUM(total_prises_en_compte) as total_prises_en_compte,
        SUM(total_decedes) as total_decedes,
        SUM(total_disparus) as total_disparus,
        ROUND(SUM(total_saines_sauves)::NUMERIC / NULLIF(SUM(total_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
        ROUND(SUM(total_decedes)::NUMERIC / NULLIF(SUM(total_prises_en_compte), 0) * 100, 2) as taux_mortalite,
        ROUND(AVG(distance_cote_moyenne_m), 0) as distance_cote_moyenne_m
    FROM v_kpi_geographique
    WHERE prefecture_maritime IS NOT NULL
    GROUP BY prefecture_maritime
    ORDER BY total_operations DESC
    """
    return execute_raw_sql(sql)


# =============================================================================
# KPIs par Type d'Opération
# =============================================================================

def get_kpi_type_operation(
    type_op: Optional[str] = None,
    categorie_evenement: Optional[str] = None
) -> list[dict]:
    """Récupérer les statistiques par type d'opération.

    Args:
        type_op: Filtrer par type (SAR, MAS, DIV, SUR, POL)
        categorie_evenement: Filtrer par catégorie d'événement

    Returns:
        Liste de dictionnaires avec stats par type
    """
    sql = """
    SELECT *
    FROM v_kpi_type_operation
    WHERE 1=1
        AND (:type_op IS NULL OR type_operation = :type_op)
        AND (:categorie IS NULL OR categorie_evenement = :categorie)
    ORDER BY nb_operations DESC
    """
    params = {"type_op": type_op, "categorie": categorie_evenement}
    return execute_raw_sql(sql, params)


# =============================================================================
# Export DataFrame pour Power BI
# =============================================================================

def export_kpi_to_dataframe(vue_name: str) -> pd.DataFrame:
    """Exporter une vue KPI complète en DataFrame.

    Utile pour l'export Power BI et analyses avancées.

    Args:
        vue_name: Nom de la vue SQL (ex: 'v_kpi_securite_mensuel')

    Returns:
        DataFrame pandas avec les données de la vue
    """
    valid_views = [
        'v_kpi_securite_mensuel',
        'v_kpi_cross_benchmark',
        'v_kpi_flotteurs_analyse',
        'v_kpi_temporel_multidim',
        'v_kpi_meteo_correlation',
        'v_kpi_yoy_comparison',
        'v_kpi_alertes_anomalies',
        'v_kpi_geographique',
        'v_kpi_type_operation'
    ]

    if vue_name not in valid_views:
        raise ValueError(f"Vue inconnue: {vue_name}. Vues valides: {valid_views}")

    sql = f"SELECT * FROM {vue_name}"
    results = execute_raw_sql(sql)
    return pd.DataFrame(results)


def export_all_kpis_to_dict() -> dict:
    """Exporter tous les KPIs principaux en dictionnaire.

    Utile pour le dashboard principal.

    Returns:
        Dictionnaire avec tous les KPIs globaux
    """
    return {
        "securite_global": get_kpi_securite_global(),
        "lives_saved": get_kpi_lives_saved(),
        "yoy_latest": get_kpi_yoy_latest(),
        "alertes_actives": get_kpi_alertes_actives(),
        "cross_benchmark": get_kpi_cross_benchmark(top_n=5),
        "flotteurs_par_categorie": get_kpi_flotteurs_par_categorie(),
        "par_prefecture": get_kpi_par_prefecture(),
        "saisonnalite": get_kpi_saisonnalite_mensuelle(),
        "phase_journee": get_kpi_phase_journee(),
    }

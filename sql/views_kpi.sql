-- =============================================================================
-- VUES KPI Analytics - SECMAR
-- =============================================================================
-- Ce script crée les vues analytiques pour les KPIs avancés.
-- Dépend de: stub_tables.sql (operations, flotteurs, resultats_humain, operations_stats)
--
-- CHOIX MÉTIER: Les indicateurs suivent la définition officielle SECMAR
-- (Programme 205 - Budget de l'État français)
-- Source: https://www.budget.gouv.fr/files/uploads/extract/2020/PLF/BG/PGM/205/FR_2020_PLF_BG_PGM_205_PERF.html
--
-- KPI PRINCIPAL: "Taux de personnes saines et sauves"
--   = (secourues + assistées + retrouvées) / (secourues + assistées + retrouvées + disparues + décédées)
--
-- Usage: psql -d secmar_db -f sql/views_kpi.sql
-- =============================================================================

SET search_path TO clean;

-- =============================================================================
-- VUE 1: v_kpi_securite_mensuel
-- Agrégation mensuelle des indicateurs de sécurité avec taux calculés
-- Utilise la définition officielle SECMAR pour le taux de sauvetage
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_securite_mensuel CASCADE;

CREATE VIEW v_kpi_securite_mensuel AS
SELECT
    DATE_TRUNC('month', o.date_heure_reception_alerte)::DATE AS periode,
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
    EXTRACT(MONTH FROM o.date_heure_reception_alerte)::INTEGER AS mois,
    COUNT(*)::INTEGER AS nb_operations,

    -- =========================================================================
    -- MÉTRIQUES OFFICIELLES SECMAR
    -- =========================================================================
    -- Numérateur officiel: personnes saines et sauves
    COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
    -- Dénominateur officiel: personnes prises en compte par le dispositif SAR
    COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
    -- KPI OFFICIEL: Taux de personnes saines et sauves (objectif: >98%)
    ROUND(
        COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_saines_sauves,

    -- =========================================================================
    -- MÉTRIQUES DÉTAILLÉES
    -- =========================================================================
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_impliques,
    COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
    COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
    COALESCE(SUM(os.nombre_secourues), 0)::INTEGER AS total_secourues,
    COALESCE(SUM(os.nombre_assistees), 0)::INTEGER AS total_assistees,
    COALESCE(SUM(os.nombre_retrouvees), 0)::INTEGER AS total_retrouvees,
    COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
    COALESCE(SUM(os.nombre_tirees_affaire_seule), 0)::INTEGER AS total_tirees_affaire_seule,
    COALESCE(SUM(os.nombre_fausses_alertes), 0)::INTEGER AS total_fausses_alertes,

    -- =========================================================================
    -- TAUX CALCULÉS
    -- =========================================================================
    -- Taux de mortalité (sur personnes prises en compte)
    ROUND(
        COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_mortalite,
    -- Taux de disparition (sur personnes prises en compte)
    ROUND(
        COALESCE(SUM(os.nombre_disparus), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_disparition,
    -- Taux de blessure (sur total impliqués)
    ROUND(
        COALESCE(SUM(os.nombre_blesses), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_impliques), 0) * 100, 2
    ) AS taux_blessure,

    -- =========================================================================
    -- INDICE DE GRAVITÉ (score composite)
    -- Formule: (décédés×3 + disparus×2 + blessés×1) / prises_en_compte
    -- =========================================================================
    ROUND(
        (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
         COALESCE(SUM(os.nombre_disparus), 0) * 2 +
         COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
    ) AS indice_gravite

FROM operations o
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY DATE_TRUNC('month', o.date_heure_reception_alerte),
         EXTRACT(YEAR FROM o.date_heure_reception_alerte),
         EXTRACT(MONTH FROM o.date_heure_reception_alerte)
ORDER BY periode DESC;

-- =============================================================================
-- VUE 2: v_kpi_cross_benchmark
-- Performance comparative par CROSS avec ranking et métriques
-- Utilise la définition officielle SECMAR pour le taux de sauvetage
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_cross_benchmark CASCADE;

CREATE VIEW v_kpi_cross_benchmark AS
WITH cross_stats AS (
    SELECT
        o."cross" AS cross_name,
        COUNT(*)::INTEGER AS nb_operations,
        -- Durées d'intervention
        AVG(
            EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte)) / 3600
        ) AS duree_moyenne_heures,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte)) / 3600
        ) AS duree_mediane_heures,
        MIN(
            EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte)) / 3600
        ) AS duree_min_heures,
        MAX(
            EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte)) / 3600
        ) AS duree_max_heures,
        -- Métriques officielles SECMAR
        COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
        COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
        -- Bilan humain détaillé
        COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
        COALESCE(SUM(os.nombre_secourues), 0)::INTEGER AS total_secourues,
        COALESCE(SUM(os.nombre_assistees), 0)::INTEGER AS total_assistees,
        COALESCE(SUM(os.nombre_retrouvees), 0)::INTEGER AS total_retrouvees,
        COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
        COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
        COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
        -- Période d'activité
        MIN(o.date_heure_reception_alerte)::DATE AS premiere_operation,
        MAX(o.date_heure_reception_alerte)::DATE AS derniere_operation,
        -- Calcul des jours d'activité
        EXTRACT(DAY FROM MAX(o.date_heure_reception_alerte) - MIN(o.date_heure_reception_alerte)) + 1 AS jours_activite
    FROM operations o
    LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
    WHERE o."cross" IS NOT NULL
    GROUP BY o."cross"
)
SELECT
    cross_name,
    nb_operations,
    -- Durées
    ROUND(duree_moyenne_heures::NUMERIC, 2) AS duree_moyenne_heures,
    ROUND(duree_mediane_heures::NUMERIC, 2) AS duree_mediane_heures,
    ROUND(duree_min_heures::NUMERIC, 2) AS duree_min_heures,
    ROUND(duree_max_heures::NUMERIC, 2) AS duree_max_heures,
    -- Métriques officielles SECMAR
    total_saines_sauves,
    total_prises_en_compte,
    -- KPI OFFICIEL: Taux de personnes saines et sauves
    ROUND(
        total_saines_sauves::NUMERIC / NULLIF(total_prises_en_compte, 0) * 100, 2
    ) AS taux_saines_sauves,
    -- Bilan détaillé
    total_personnes,
    total_secourues,
    total_assistees,
    total_retrouvees,
    total_decedes,
    total_disparus,
    total_blesses,
    -- Taux de mortalité (sur prises en compte)
    ROUND(
        total_decedes::NUMERIC / NULLIF(total_prises_en_compte, 0) * 100, 2
    ) AS taux_mortalite,
    -- Charge de travail
    ROUND(
        nb_operations::NUMERIC / NULLIF(jours_activite, 0), 2
    ) AS operations_par_jour,
    ROUND(
        total_personnes::NUMERIC / NULLIF(nb_operations, 0), 2
    ) AS personnes_par_operation,
    -- Rankings (basés sur le KPI officiel)
    RANK() OVER (ORDER BY nb_operations DESC) AS rank_volume,
    RANK() OVER (ORDER BY total_saines_sauves::NUMERIC / NULLIF(total_prises_en_compte, 0) DESC NULLS LAST) AS rank_sauvetage,
    RANK() OVER (ORDER BY duree_mediane_heures ASC NULLS LAST) AS rank_rapidite,
    -- Période
    premiere_operation,
    derniere_operation
FROM cross_stats
ORDER BY nb_operations DESC;

-- =============================================================================
-- VUE 3: v_kpi_flotteurs_analyse
-- Statistiques détaillées par type et catégorie de flotteur
-- Utilise la définition officielle SECMAR pour le taux de sauvetage
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_flotteurs_analyse CASCADE;

CREATE VIEW v_kpi_flotteurs_analyse AS
WITH flotteur_stats AS (
    SELECT
        f.type_flotteur,
        f.categorie_flotteur,
        f.resultat_flotteur,
        COUNT(DISTINCT f.operation_id)::INTEGER AS nb_operations,
        COUNT(*)::INTEGER AS nb_flotteurs,
        -- Métriques officielles SECMAR
        COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
        COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
        -- Bilan détaillé
        COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
        COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
        COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
        COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
        AVG(o.distance_cote_metres) AS distance_cote_moyenne_m,
        AVG(o.distance_cote_milles_nautiques) AS distance_cote_moyenne_nm
    FROM flotteurs f
    JOIN operations o ON f.operation_id = o.operation_id
    LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
    GROUP BY f.type_flotteur, f.categorie_flotteur, f.resultat_flotteur
),
totaux AS (
    SELECT SUM(nb_operations) AS total_ops FROM flotteur_stats
)
SELECT
    fs.type_flotteur,
    fs.categorie_flotteur,
    fs.resultat_flotteur,
    fs.nb_operations,
    fs.nb_flotteurs,
    -- Pourcentage du total
    ROUND(
        fs.nb_operations::NUMERIC / NULLIF(t.total_ops, 0) * 100, 2
    ) AS pct_operations,
    -- Métriques officielles SECMAR
    fs.total_saines_sauves,
    fs.total_prises_en_compte,
    -- KPI OFFICIEL: Taux de personnes saines et sauves
    ROUND(
        fs.total_saines_sauves::NUMERIC / NULLIF(fs.total_prises_en_compte, 0) * 100, 2
    ) AS taux_saines_sauves,
    -- Bilan détaillé
    fs.total_personnes,
    fs.total_decedes,
    fs.total_disparus,
    fs.total_blesses,
    -- Taux de mortalité (sur prises en compte)
    ROUND(
        fs.total_decedes::NUMERIC / NULLIF(fs.total_prises_en_compte, 0) * 100, 2
    ) AS taux_mortalite,
    -- Distance côte
    ROUND(fs.distance_cote_moyenne_m::NUMERIC, 0) AS distance_cote_moyenne_m,
    ROUND(fs.distance_cote_moyenne_nm::NUMERIC, 2) AS distance_cote_moyenne_nm,
    -- Personnes par opération
    ROUND(
        fs.total_personnes::NUMERIC / NULLIF(fs.nb_operations, 0), 2
    ) AS personnes_par_operation
FROM flotteur_stats fs
CROSS JOIN totaux t
ORDER BY fs.nb_operations DESC;

-- =============================================================================
-- VUE 4: v_kpi_temporel_multidim
-- Analyse croisée temporelle multi-dimensions
-- Utilise la définition officielle SECMAR
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_temporel_multidim CASCADE;

CREATE VIEW v_kpi_temporel_multidim AS
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
    EXTRACT(MONTH FROM o.date_heure_reception_alerte)::INTEGER AS mois,
    EXTRACT(DOW FROM o.date_heure_reception_alerte)::INTEGER AS jour_semaine, -- 0=Dimanche
    TO_CHAR(o.date_heure_reception_alerte, 'Day') AS nom_jour,
    o.phase_journee,
    o.est_jour_ferie,
    o.est_vacances_scolaires,
    o.maree_categorie,
    -- Comptages
    COUNT(*)::INTEGER AS nb_operations,
    -- Métriques officielles SECMAR
    COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
    COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
    -- Bilan détaillé
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
    COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
    COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
    -- Victimes (décédés + disparus)
    COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
    -- Moyennes
    ROUND(AVG(os.nombre_impliques)::NUMERIC, 2) AS moy_personnes_par_op,
    -- KPI OFFICIEL: Taux de personnes saines et sauves
    ROUND(
        COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_saines_sauves,
    -- Indice de gravité
    ROUND(
        (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
         COALESCE(SUM(os.nombre_disparus), 0) * 2 +
         COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
    ) AS indice_gravite
FROM operations o
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY
    EXTRACT(YEAR FROM o.date_heure_reception_alerte),
    EXTRACT(MONTH FROM o.date_heure_reception_alerte),
    EXTRACT(DOW FROM o.date_heure_reception_alerte),
    TO_CHAR(o.date_heure_reception_alerte, 'Day'),
    o.phase_journee,
    o.est_jour_ferie,
    o.est_vacances_scolaires,
    o.maree_categorie
ORDER BY annee DESC, mois DESC, nb_operations DESC;

-- =============================================================================
-- VUE 5: v_kpi_meteo_correlation
-- Corrélations météo / incidents pour analyses
-- Utilise la définition officielle SECMAR
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_meteo_correlation CASCADE;

CREATE VIEW v_kpi_meteo_correlation AS
SELECT
    o.vent_force,
    o.mer_force,
    o.vent_direction_categorie,
    o.maree_categorie,
    o.maree_coefficient,
    -- Comptages
    COUNT(*)::INTEGER AS nb_operations,
    -- Métriques officielles SECMAR
    COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
    COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
    -- Bilan détaillé
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
    COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
    COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
    COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
    -- Victimes
    COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
    -- Moyennes
    ROUND(AVG(os.nombre_impliques)::NUMERIC, 2) AS moy_personnes_par_op,
    -- KPI OFFICIEL: Taux de personnes saines et sauves
    ROUND(
        COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_saines_sauves,
    -- Taux de mortalité (sur prises en compte)
    ROUND(
        COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_mortalite,
    -- Indice de gravité
    ROUND(
        (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
         COALESCE(SUM(os.nombre_disparus), 0) * 2 +
         COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
    ) AS indice_gravite
FROM operations o
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE o.vent_force IS NOT NULL OR o.mer_force IS NOT NULL
GROUP BY
    o.vent_force,
    o.mer_force,
    o.vent_direction_categorie,
    o.maree_categorie,
    o.maree_coefficient
ORDER BY nb_operations DESC;

-- =============================================================================
-- VUE 6: v_kpi_yoy_comparison
-- Comparatifs année sur année pour tous les KPIs
-- Utilise la définition officielle SECMAR
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_yoy_comparison CASCADE;

CREATE VIEW v_kpi_yoy_comparison AS
WITH yearly_stats AS (
    SELECT
        EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
        COUNT(*)::INTEGER AS nb_operations,
        -- Métriques officielles SECMAR
        COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
        COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
        -- Bilan détaillé
        COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
        COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
        COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
        COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
        AVG(
            EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte)) / 3600
        ) AS duree_moyenne_heures
    FROM operations o
    LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
    WHERE o.date_heure_reception_alerte IS NOT NULL
    GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)
)
SELECT
    y.annee,
    y.nb_operations,
    -- Métriques officielles SECMAR
    y.total_saines_sauves,
    y.total_prises_en_compte,
    -- KPI OFFICIEL: Taux de personnes saines et sauves
    ROUND(
        y.total_saines_sauves::NUMERIC / NULLIF(y.total_prises_en_compte, 0) * 100, 2
    ) AS taux_saines_sauves,
    -- Bilan détaillé
    y.total_personnes,
    y.total_decedes,
    y.total_disparus,
    y.total_blesses,
    ROUND(y.duree_moyenne_heures::NUMERIC, 2) AS duree_moyenne_heures,
    -- Taux de mortalité (sur prises en compte)
    ROUND(
        y.total_decedes::NUMERIC / NULLIF(y.total_prises_en_compte, 0) * 100, 2
    ) AS taux_mortalite,
    -- YoY comparisons (vs année précédente)
    LAG(y.nb_operations) OVER (ORDER BY y.annee) AS ops_annee_precedente,
    ROUND(
        (y.nb_operations - LAG(y.nb_operations) OVER (ORDER BY y.annee))::NUMERIC /
        NULLIF(LAG(y.nb_operations) OVER (ORDER BY y.annee), 0) * 100, 2
    ) AS yoy_operations_pct,
    LAG(y.total_personnes) OVER (ORDER BY y.annee) AS personnes_annee_precedente,
    ROUND(
        (y.total_personnes - LAG(y.total_personnes) OVER (ORDER BY y.annee))::NUMERIC /
        NULLIF(LAG(y.total_personnes) OVER (ORDER BY y.annee), 0) * 100, 2
    ) AS yoy_personnes_pct,
    LAG(y.total_saines_sauves) OVER (ORDER BY y.annee) AS sauves_annee_precedente,
    ROUND(
        (y.total_saines_sauves - LAG(y.total_saines_sauves) OVER (ORDER BY y.annee))::NUMERIC /
        NULLIF(LAG(y.total_saines_sauves) OVER (ORDER BY y.annee), 0) * 100, 2
    ) AS yoy_sauves_pct,
    LAG(y.total_decedes) OVER (ORDER BY y.annee) AS decedes_annee_precedente,
    y.total_decedes - LAG(y.total_decedes) OVER (ORDER BY y.annee) AS yoy_decedes_diff
FROM yearly_stats y
ORDER BY y.annee DESC;

-- =============================================================================
-- VUE 7: v_kpi_alertes_anomalies
-- Détection d'écarts significatifs pour système d'alertes
-- Utilise une MOYENNE MOBILE 12 MOIS pour des z-scores stables
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_alertes_anomalies CASCADE;

CREATE VIEW v_kpi_alertes_anomalies AS
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
    GROUP BY DATE_TRUNC('month', o.date_heure_reception_alerte)
),
-- Moyenne mobile sur les 12 mois précédents (exclut le mois courant)
stats_rolling AS (
    SELECT
        m.periode,
        AVG(m2.nb_operations) AS moy_operations,
        STDDEV(m2.nb_operations) AS std_operations,
        AVG(m2.total_personnes) AS moy_personnes,
        STDDEV(m2.total_personnes) AS std_personnes,
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
    -- Écarts par rapport à la moyenne mobile
    ROUND((m.nb_operations - sr.moy_operations)::NUMERIC, 2) AS ecart_operations,
    ROUND((m.total_personnes - sr.moy_personnes)::NUMERIC, 2) AS ecart_personnes,
    ROUND((m.total_victimes - sr.moy_victimes)::NUMERIC, 2) AS ecart_victimes,
    -- Z-scores basés sur moyenne mobile 12 mois
    ROUND(
        (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0), 2
    ) AS zscore_operations,
    ROUND(
        (m.total_personnes - sr.moy_personnes) / NULLIF(sr.std_personnes, 0), 2
    ) AS zscore_personnes,
    ROUND(
        (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0), 2
    ) AS zscore_victimes,
    -- Alertes (seuils: Z>1.5 ATTENTION, Z>2.5 ALERTE)
    CASE
        WHEN (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0) > 2.5 THEN 'ALERTE'
        WHEN (m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0) > 1.5 THEN 'ATTENTION'
        ELSE 'NORMAL'
    END AS niveau_alerte_victimes,
    CASE
        WHEN (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0) > 2.5 THEN 'ALERTE'
        WHEN (m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0) > 1.5 THEN 'ATTENTION'
        ELSE 'NORMAL'
    END AS niveau_alerte_operations,
    -- Moyennes de référence (moyenne mobile 12 mois)
    ROUND(sr.moy_operations::NUMERIC, 2) AS moyenne_operations,
    ROUND(sr.moy_personnes::NUMERIC, 2) AS moyenne_personnes,
    ROUND(sr.moy_victimes::NUMERIC, 2) AS moyenne_victimes
FROM monthly_stats m
LEFT JOIN stats_rolling sr ON m.periode = sr.periode
ORDER BY m.periode DESC;

-- =============================================================================
-- VUE 8: v_kpi_geographique
-- Analyse géographique par zone et département
-- Utilise la définition officielle SECMAR
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_geographique CASCADE;

CREATE VIEW v_kpi_geographique AS
SELECT
    o.prefecture_maritime,
    o."cross" AS cross_name,
    o.departement,
    o.zone_responsabilite,
    o.est_metropolitain,
    -- Comptages
    COUNT(*)::INTEGER AS nb_operations,
    -- Métriques officielles SECMAR
    COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
    COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
    -- Bilan détaillé
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
    COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
    COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
    -- Coordonnées moyennes (centroïde)
    ROUND(AVG(o.latitude)::NUMERIC, 4) AS lat_moyenne,
    ROUND(AVG(o.longitude)::NUMERIC, 4) AS lon_moyenne,
    -- Distance côte
    ROUND(AVG(o.distance_cote_metres)::NUMERIC, 0) AS distance_cote_moyenne_m,
    -- Zones spéciales
    SUM(CASE WHEN o.est_dans_stm THEN 1 ELSE 0 END)::INTEGER AS nb_dans_stm,
    SUM(CASE WHEN o.est_dans_dst THEN 1 ELSE 0 END)::INTEGER AS nb_dans_dst,
    -- KPI OFFICIEL: Taux de personnes saines et sauves
    ROUND(
        COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_saines_sauves,
    -- Taux de mortalité (sur prises en compte)
    ROUND(
        COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_mortalite
FROM operations o
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
GROUP BY
    o.prefecture_maritime,
    o."cross",
    o.departement,
    o.zone_responsabilite,
    o.est_metropolitain
ORDER BY nb_operations DESC;

-- =============================================================================
-- VUE 9: v_kpi_type_operation
-- Analyse par type et sous-type d'opération
-- Utilise la définition officielle SECMAR
-- =============================================================================
DROP VIEW IF EXISTS v_kpi_type_operation CASCADE;

CREATE VIEW v_kpi_type_operation AS
SELECT
    o.type_operation,
    o.sous_type_operation,
    o.evenement,
    o.categorie_evenement,
    -- Comptages
    COUNT(*)::INTEGER AS nb_operations,
    -- Métriques officielles SECMAR
    COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
    COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
    -- Bilan détaillé
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
    COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
    COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
    COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
    -- Moyennes
    ROUND(AVG(os.nombre_impliques)::NUMERIC, 2) AS moy_personnes_par_op,
    -- Durée moyenne
    ROUND(
        AVG(EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte)) / 3600)::NUMERIC, 2
    ) AS duree_moyenne_heures,
    -- KPI OFFICIEL: Taux de personnes saines et sauves
    ROUND(
        COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_saines_sauves,
    -- Taux de mortalité (sur prises en compte)
    ROUND(
        COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2
    ) AS taux_mortalite,
    -- Indice gravité
    ROUND(
        (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
         COALESCE(SUM(os.nombre_disparus), 0) * 2 +
         COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
    ) AS indice_gravite
FROM operations o
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
GROUP BY
    o.type_operation,
    o.sous_type_operation,
    o.evenement,
    o.categorie_evenement
ORDER BY nb_operations DESC;

-- =============================================================================
-- Index pour performances des vues
-- =============================================================================

-- INDEX CRITIQUES pour les jointures FK (impact majeur sur performance)
-- Note: operations_stats est une VIEW, pas une table - l'index est sur resultats_humain
CREATE INDEX IF NOT EXISTS idx_resultats_humain_operation_id ON resultats_humain(operation_id);
CREATE INDEX IF NOT EXISTS idx_flotteurs_operation_id ON flotteurs(operation_id);

-- INDEX pour les colonnes fréquemment filtrées/triées
CREATE INDEX IF NOT EXISTS idx_operations_date_reception ON operations(date_heure_reception_alerte);
CREATE INDEX IF NOT EXISTS idx_operations_cross ON operations("cross");
CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(type_operation);

-- INDEX composite pour les requêtes filtrées par CROSS + date
CREATE INDEX IF NOT EXISTS idx_operations_cross_date ON operations("cross", date_heure_reception_alerte);

-- INDEX existants (pour dimensions d'analyse)
CREATE INDEX IF NOT EXISTS idx_operations_phase_journee ON operations(phase_journee);
CREATE INDEX IF NOT EXISTS idx_operations_jour_ferie ON operations(est_jour_ferie);
CREATE INDEX IF NOT EXISTS idx_operations_vacances ON operations(est_vacances_scolaires);
CREATE INDEX IF NOT EXISTS idx_operations_vent ON operations(vent_force);
CREATE INDEX IF NOT EXISTS idx_operations_mer ON operations(mer_force);
CREATE INDEX IF NOT EXISTS idx_operations_maree ON operations(maree_categorie);
CREATE INDEX IF NOT EXISTS idx_flotteurs_type ON flotteurs(type_flotteur);
CREATE INDEX IF NOT EXISTS idx_flotteurs_categorie ON flotteurs(categorie_flotteur);

-- =============================================================================
-- Vérification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '=== Vues KPI Analytics créées avec succès ===';
    RAISE NOTICE '';
    RAISE NOTICE 'Vues disponibles:';
    RAISE NOTICE '  1. v_kpi_securite_mensuel    - Taux de sécurité mensuels';
    RAISE NOTICE '  2. v_kpi_cross_benchmark     - Performance CROSS avec ranking';
    RAISE NOTICE '  3. v_kpi_flotteurs_analyse   - Stats par type de flotteur';
    RAISE NOTICE '  4. v_kpi_temporel_multidim   - Analyse temporelle croisée';
    RAISE NOTICE '  5. v_kpi_meteo_correlation   - Corrélations météo/gravité';
    RAISE NOTICE '  6. v_kpi_yoy_comparison      - Comparatifs Year-over-Year';
    RAISE NOTICE '  7. v_kpi_alertes_anomalies   - Détection anomalies (z-scores)';
    RAISE NOTICE '  8. v_kpi_geographique        - Analyse par zone géographique';
    RAISE NOTICE '  9. v_kpi_type_operation      - Stats par type opération';
END $$;

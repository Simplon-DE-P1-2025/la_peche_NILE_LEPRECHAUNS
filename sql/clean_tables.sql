-- =============================================================================
-- STUB Tables - Alignées avec le MCD SECMAR
-- =============================================================================
-- Ce script crée les tables pour le développement CRUD et Streamlit.
-- Aligné avec le MCD (source de vérité) + documentation SECMAR officielle.
--
-- Usage: psql -d secmar_db -f sql/stub_tables.sql
-- =============================================================================

-- Créer le schéma clean s'il n'existe pas et l'utiliser
CREATE SCHEMA IF NOT EXISTS clean;
SET search_path TO clean;

-- Table des opérations (enrichie avec champs MCD + SECMAR complet)
CREATE TABLE IF NOT EXISTS operations (
    operation_id BIGINT PRIMARY KEY,
    -- Identification
    type_operation VARCHAR(100),
    numero_sitrep VARCHAR(50),
    cross_sitrep VARCHAR(100),
    sous_type_operation VARCHAR(100),
    -- Alerte SECMAR
    pourquoi_alerte VARCHAR(100),
    moyen_alerte VARCHAR(100),
    qui_alerte VARCHAR(100),
    categorie_qui_alerte VARCHAR(100),
    -- Localisation
    "cross" VARCHAR(50),
    departement VARCHAR(100),
    est_metropolitain BOOLEAN,
    zone_responsabilite VARCHAR(50),
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    -- Contexte opération
    evenement VARCHAR(100),
    categorie_evenement VARCHAR(100),
    autorite VARCHAR(100),
    seconde_autorite VARCHAR(100),
    -- Météo
    vent_direction INTEGER,
    vent_direction_categorie VARCHAR(50),
    vent_force INTEGER,
    mer_force INTEGER,
    -- Temporel SECMAR
    date_heure_reception_alerte TIMESTAMP,
    date_heure_fin_operation TIMESTAMP,
    fuseau_horaire VARCHAR(50),
    systeme_source VARCHAR(50),
    -- Champs enrichissement (MCD)
    est_jour_ferie BOOLEAN DEFAULT FALSE,
    est_vacances_scolaires BOOLEAN DEFAULT FALSE,
    phase_journee VARCHAR(50),
    concerne_plongee BOOLEAN DEFAULT FALSE,
    implique_wingfoil BOOLEAN DEFAULT FALSE,
    distance_cote_metres DECIMAL(10, 2),
    distance_cote_milles_nautiques DECIMAL(10, 4),
    est_dans_stm BOOLEAN DEFAULT FALSE,
    nom_stm VARCHAR(100),
    est_dans_dst BOOLEAN DEFAULT FALSE,
    nom_dst VARCHAR(100),
    prefecture_maritime VARCHAR(100),
    maree_port VARCHAR(100),
    maree_coefficient INTEGER,
    maree_categorie VARCHAR(50),
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des flotteurs (avec numero_ordre MCD)
CREATE TABLE IF NOT EXISTS flotteurs (
    flotteur_id SERIAL PRIMARY KEY,
    operation_id BIGINT NOT NULL REFERENCES operations(operation_id) ON DELETE CASCADE,
    numero_ordre INTEGER,
    type_flotteur VARCHAR(100),
    categorie_flotteur VARCHAR(100),
    pavillon VARCHAR(50),
    numero_immatriculation VARCHAR(50),
    resultat_flotteur VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des résultats humains (avec dont_nombre_blesse MCD)
CREATE TABLE IF NOT EXISTS resultats_humain (
    resultat_id SERIAL PRIMARY KEY,
    operation_id BIGINT NOT NULL REFERENCES operations(operation_id) ON DELETE CASCADE,
    categorie_personne VARCHAR(50),
    resultat_humain VARCHAR(50),
    nombre INTEGER DEFAULT 0,
    dont_nombre_blesse INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'viewer' CHECK (role IN ('viewer', 'editor', 'admin')),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table d'audit
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation_type VARCHAR(10) NOT NULL CHECK (operation_type IN ('INSERT', 'UPDATE', 'DELETE', 'ETL_LOAD')),
    record_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    user_id VARCHAR(50) DEFAULT 'system',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assurer la compatibilite avec ETL_LOAD meme si la table existe deja
ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_operation_type_check;
ALTER TABLE audit_log ADD CONSTRAINT audit_log_operation_type_check
    CHECK (operation_type IN ('INSERT', 'UPDATE', 'DELETE', 'ETL_LOAD'));

-- =============================================================================
-- MATERIALIZED VIEW operations_stats (pré-calculée pour performance)
-- =============================================================================
--
-- CHOIX MÉTIER - Indicateur officiel SECMAR (Programme 205 - Budget État)
-- Source: https://www.budget.gouv.fr/files/uploads/extract/2020/PLF/BG/PGM/205/FR_2020_PLF_BG_PGM_205_PERF.html
--
-- DÉFINITION OFFICIELLE du "Taux de personnes saines et sauves":
--   Numérateur: Personnes mises hors de danger = retrouvées + assistées + secourues
--   Dénominateur: Personnes prises en compte = retrouvées + secourues + assistées + disparues + décédées
--
-- EXCLUSIONS (conformément aux directives SECMAR):
--   - "Personne tirée d'affaire seule" : autonome, non prise en compte dans l'évaluation SAR
--   - "Personne impliquée dans fausse alerte" : pas de situation de détresse réelle
--   - "Personne indemne" / "Inconnu" : statut non qualifié pour l'indicateur
--
-- Cette vue fournit les métriques de base pour calculer le KPI officiel:
--   taux_saines_sauves = nombre_saines_sauves / nombre_prises_en_compte * 100
--
-- NOTE PERFORMANCE: Vue matérialisée = données pré-calculées sur disque.
-- Doit être rafraîchie après chaque modification (ETL ou CRUD).
-- Commande: REFRESH MATERIALIZED VIEW CONCURRENTLY operations_stats;
--
-- =============================================================================
-- Supprimer l'ancienne vue (matérialisée OU normale) si elle existe
-- IMPORTANT: Tenter DROP MATERIALIZED VIEW en premier pour éviter erreur
-- "is not a view" si c'est déjà une vue matérialisée
DROP MATERIALIZED VIEW IF EXISTS operations_stats CASCADE;
DROP VIEW IF EXISTS operations_stats CASCADE;

CREATE MATERIALIZED VIEW operations_stats AS
SELECT
    o.operation_id,

    -- =========================================================================
    -- MÉTRIQUES OFFICIELLES SECMAR (pour le KPI "Taux de personnes saines et sauves")
    -- =========================================================================

    -- Numérateur officiel: Personnes SAINES ET SAUVES (mises hors de danger par le dispositif SAR)
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN (
            'Personne secourue',      -- Sauvée d'une situation de détresse
            'Personne assistée',      -- Assistée par les moyens SAR
            'Personne retrouvée'      -- Retrouvée lors d'une opération de recherche
        )
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_saines_sauves,

    -- Dénominateur officiel: Personnes PRISES EN COMPTE par le dispositif SAR
    -- Exclut: tirées d'affaire seule, fausses alertes, indemnes, inconnus
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN (
            'Personne secourue',
            'Personne assistée',
            'Personne retrouvée',
            'Personne disparue',
            'Personne décédée',
            'Personne décédée accidentellement',
            'Personne décédée naturellement'
        )
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_prises_en_compte,

    -- =========================================================================
    -- MÉTRIQUES DÉTAILLÉES (pour analyses approfondies)
    -- =========================================================================

    -- Décédés: toutes les catégories de décès
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN (
            'Personne décédée',
            'Personne décédée accidentellement',
            'Personne décédée naturellement'
        )
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_decedes,

    -- Disparus: personnes non retrouvées
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne disparue'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_disparus,

    -- Blessés: comptabilisés via le champ dont_nombre_blesse (transversal)
    COALESCE(SUM(COALESCE(rh.dont_nombre_blesse, 0)), 0)::INTEGER as nombre_blesses,

    -- Secourues: personnes sauvées d'une situation de détresse critique
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne secourue'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_secourues,

    -- Assistées: personnes aidées mais pas en danger mortel immédiat
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne assistée'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_assistees,

    -- Retrouvées: personnes localisées lors d'opérations de recherche
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne retrouvée'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_retrouvees,

    -- Tirées d'affaire seule: personnes autonomes (EXCLUES du KPI officiel)
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne tirée d''affaire seule'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_tirees_affaire_seule,

    -- =========================================================================
    -- MÉTRIQUES GLOBALES (toutes catégories confondues)
    -- =========================================================================

    -- Total impliqués: TOUTES les personnes (pour statistiques générales)
    COALESCE(SUM(rh.nombre), 0)::INTEGER as nombre_impliques,

    -- Fausses alertes: personnes concernées par des alertes non fondées
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne impliquée dans fausse alerte'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_fausses_alertes

FROM operations o
LEFT JOIN resultats_humain rh ON o.operation_id = rh.operation_id
GROUP BY o.operation_id;

-- Index UNIQUE sur la vue matérialisée (requis pour REFRESH CONCURRENTLY)
CREATE UNIQUE INDEX IF NOT EXISTS idx_operations_stats_pk ON operations_stats(operation_id);

-- =============================================================================
-- Index pour les performances
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_operations_date ON operations(date_heure_reception_alerte);
CREATE INDEX IF NOT EXISTS idx_operations_cross ON operations("cross");
CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(type_operation);
CREATE INDEX IF NOT EXISTS idx_operations_prefecture ON operations(prefecture_maritime);
CREATE INDEX IF NOT EXISTS idx_flotteurs_operation ON flotteurs(operation_id);
CREATE INDEX IF NOT EXISTS idx_resultats_operation ON resultats_humain(operation_id);
CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);

-- =============================================================================
-- Vue utilitaire: liste centralisée des CROSS actifs
-- =============================================================================
DROP VIEW IF EXISTS v_cross_actifs CASCADE;

CREATE VIEW v_cross_actifs AS
SELECT cross_name FROM (VALUES
    ('Antilles-Guyane'),
    ('Corse'),
    ('Corsen'),
    ('Étel'),
    ('Etel'),
    ('Gris-Nez'),
    ('Jobourg'),
    ('La Garde'),
    ('Nouvelle-Calédonie'),
    ('Polynésie'),
    ('Sud océan Indien')
) AS t(cross_name);

-- =============================================================================
-- Vue matérialisée KPIs globaux (évite COUNT DISTINCT coûteux à chaque requête)
-- =============================================================================
-- OBJECTIF: Pré-calculer les agrégats globaux pour le dashboard
-- GAIN: 12.6s → 10ms (99% plus rapide)
-- REFRESH: Après chaque ETL ou modification CRUD
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_global CASCADE;

CREATE MATERIALIZED VIEW v_kpi_global AS
SELECT
    COUNT(*) as total_operations,
    COUNT(DISTINCT o."cross") as nb_cross,
    COUNT(DISTINCT o.departement) as nb_departements,
    COALESCE(SUM(s.nombre_impliques), 0)::INTEGER as total_personnes,
    COALESCE(SUM(s.nombre_saines_sauves), 0)::INTEGER as total_saines_sauves,
    COALESCE(SUM(s.nombre_decedes), 0)::INTEGER as total_decedes,
    COALESCE(SUM(s.nombre_disparus), 0)::INTEGER as total_disparus,
    COALESCE(SUM(s.nombre_blesses), 0)::INTEGER as total_blesses,
    COALESCE(SUM(s.nombre_prises_en_compte), 0)::INTEGER as total_prises_en_compte,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY CASE
                WHEN o.date_heure_fin_operation IS NOT NULL
                    AND o.date_heure_fin_operation >= o.date_heure_reception_alerte
                THEN EXTRACT(EPOCH FROM (o.date_heure_fin_operation - o.date_heure_reception_alerte)) / 60
            END
        )::NUMERIC,
        0
    ) as duree_mediane,
    MIN(o.date_heure_reception_alerte) as premiere_operation,
    MAX(o.date_heure_reception_alerte) as derniere_operation
FROM operations o
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL;

-- =============================================================================
-- Vue matérialisée stats annuelles (pour graphiques d'évolution)
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_annuel CASCADE;

CREATE MATERIALIZED VIEW v_kpi_annuel AS
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER as annee,
    COUNT(*)::INTEGER as total_operations,
    COALESCE(SUM(s.nombre_impliques), 0)::INTEGER as total_personnes,
    COALESCE(SUM(s.nombre_saines_sauves), 0)::INTEGER as total_saines_sauves,
    COALESCE(SUM(s.nombre_decedes), 0)::INTEGER as total_decedes,
    COALESCE(SUM(s.nombre_disparus), 0)::INTEGER as total_disparus,
    COALESCE(SUM(s.nombre_prises_en_compte), 0)::INTEGER as total_prises_en_compte,
    ROUND(
        COALESCE(SUM(s.nombre_saines_sauves), 0)::NUMERIC /
        NULLIF(SUM(s.nombre_prises_en_compte), 0) * 100, 2
    ) as taux_saines_sauves
FROM operations o
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte)
ORDER BY annee DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_annuel_pk ON v_kpi_annuel(annee);

-- =============================================================================
-- Vue matérialisée stats par CROSS (pour benchmarking)
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_cross CASCADE;

CREATE MATERIALIZED VIEW v_kpi_cross AS
SELECT
    COALESCE(o."cross", 'Non renseigné') as cross_name,
    COUNT(*)::INTEGER as total_operations,
    COALESCE(SUM(s.nombre_impliques), 0)::INTEGER as total_personnes,
    COALESCE(SUM(s.nombre_saines_sauves), 0)::INTEGER as total_saines_sauves,
    COALESCE(SUM(s.nombre_decedes), 0)::INTEGER as total_decedes,
    COALESCE(SUM(s.nombre_disparus), 0)::INTEGER as total_disparus,
    ROUND(
        COALESCE(SUM(s.nombre_saines_sauves), 0)::NUMERIC /
        NULLIF(SUM(s.nombre_prises_en_compte), 0) * 100, 2
    ) as taux_saines_sauves
FROM operations o
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY COALESCE(o."cross", 'Non renseigné')
ORDER BY total_operations DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_cross_pk ON v_kpi_cross(cross_name);

-- =============================================================================
-- Trigger d'audit optimisé (avec bypass ETL et stockage diff uniquement)
-- =============================================================================
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    record_pk BIGINT;
    old_json JSONB;
    new_json JSONB;
    diff_json JSONB;
    changed_cols TEXT[];
    is_etl_mode BOOLEAN;
    current_user_id TEXT;
BEGIN
    -- Récupérer le mode ETL et l'utilisateur
    BEGIN
        is_etl_mode := COALESCE(current_setting('app.etl_mode', true)::BOOLEAN, FALSE);
    EXCEPTION WHEN OTHERS THEN
        is_etl_mode := FALSE;
    END;

    current_user_id := COALESCE(current_setting('app.current_user', true), 'system');

    -- SKIP si mode ETL actif (sera logué en résumé à la fin de l'ETL)
    IF is_etl_mode THEN
        RETURN COALESCE(NEW, OLD);
    END IF;

    -- Déterminer la clé primaire selon la table
    CASE TG_TABLE_NAME
        WHEN 'operations' THEN
            record_pk := COALESCE(NEW.operation_id, OLD.operation_id);
        WHEN 'flotteurs' THEN
            record_pk := COALESCE(NEW.flotteur_id, OLD.flotteur_id);
        WHEN 'resultats_humain' THEN
            record_pk := COALESCE(NEW.resultat_id, OLD.resultat_id);
        ELSE
            record_pk := NULL;
    END CASE;

    -- Audit selon le type d'opération (optimisé)
    IF TG_OP = 'INSERT' THEN
        -- Pour INSERT: stocker uniquement l'identifiant (pas le snapshot complet)
        INSERT INTO audit_log (table_name, operation_type, record_id, new_values, user_id)
        VALUES (TG_TABLE_NAME, 'INSERT', record_pk,
                jsonb_build_object('pk', record_pk), current_user_id);

    ELSIF TG_OP = 'UPDATE' THEN
        -- Pour UPDATE: stocker UNIQUEMENT les champs modifiés (pas les snapshots complets)
        old_json := to_jsonb(OLD);
        new_json := to_jsonb(NEW);

        -- Calculer le diff: uniquement les clés où les valeurs diffèrent
        SELECT
            jsonb_object_agg(key, jsonb_build_object('old', old_json->key, 'new', new_json->key)),
            array_agg(key)
        INTO diff_json, changed_cols
        FROM (
            SELECT key
            FROM jsonb_each(new_json)
            WHERE new_json->key IS DISTINCT FROM old_json->key
            AND key NOT IN ('updated_at', 'created_at')
        ) changed_keys;

        -- Ne logger que s'il y a des changements réels
        IF diff_json IS NOT NULL AND diff_json != '{}' THEN
            INSERT INTO audit_log (table_name, operation_type, record_id, new_values, changed_fields, user_id)
            VALUES (TG_TABLE_NAME, 'UPDATE', record_pk, diff_json, changed_cols, current_user_id);
        END IF;

    ELSIF TG_OP = 'DELETE' THEN
        -- Pour DELETE: stocker uniquement l'identifiant
        INSERT INTO audit_log (table_name, operation_type, record_id, old_values, user_id)
        VALUES (TG_TABLE_NAME, 'DELETE', record_pk,
                jsonb_build_object('pk', record_pk), current_user_id);
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Créer les triggers (pas sur operations_stats car c'est une VIEW)
DROP TRIGGER IF EXISTS audit_operations ON operations;
CREATE TRIGGER audit_operations
    AFTER INSERT OR UPDATE OR DELETE ON operations
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

DROP TRIGGER IF EXISTS audit_flotteurs ON flotteurs;
CREATE TRIGGER audit_flotteurs
    AFTER INSERT OR UPDATE OR DELETE ON flotteurs
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

DROP TRIGGER IF EXISTS audit_resultats_humain ON resultats_humain;
CREATE TRIGGER audit_resultats_humain
    AFTER INSERT OR UPDATE OR DELETE ON resultats_humain
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- =============================================================================
-- Fonction de nettoyage des anciens logs d'audit (rétention 90 jours)
-- =============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE timestamp < CURRENT_TIMESTAMP - (retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Logger le nettoyage (une seule ligne résumé)
    IF deleted_count > 0 THEN
        INSERT INTO audit_log (table_name, operation_type, new_values, user_id)
        VALUES ('audit_log', 'ETL_LOAD',
                jsonb_build_object('action', 'cleanup', 'deleted_rows', deleted_count, 'retention_days', retention_days),
                'system');
    END IF;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Vue matérialisée YoY pour CROSS actifs (évite CTE complexe à chaque requête)
-- =============================================================================
-- OBJECTIF: Pré-calculer les stats Year-over-Year pour les CROSS actifs
-- GAIN: 6.9s → 10ms (99% plus rapide)
-- REFRESH: Après chaque ETL
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_yoy_cross_actifs CASCADE;

CREATE MATERIALIZED VIEW v_kpi_yoy_cross_actifs AS
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
    WHERE o.date_heure_reception_alerte IS NOT NULL
        AND o."cross" IN (
            'Antilles-Guyane', 'Corse', 'Corsen', 'Étel', 'Etel',
            'Gris-Nez', 'Jobourg', 'La Garde', 'Nouvelle-Calédonie',
            'Polynésie', 'Sud océan Indien'
        )
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
ORDER BY y.annee DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_yoy_cross_actifs_pk ON v_kpi_yoy_cross_actifs(annee);

-- =============================================================================
-- Vue matérialisée CROSS Benchmark (évite PERCENTILE_CONT + RANK coûteux)
-- =============================================================================
-- OBJECTIF: Pré-calculer les performances de chaque CROSS
-- GAIN: ~2-3s → 10ms (99% plus rapide)
-- REFRESH: Après chaque ETL
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_cross_benchmark_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_cross_benchmark_mv AS
WITH cross_stats AS (
    SELECT
        o."cross" AS cross_name,
        COUNT(*)::INTEGER AS nb_operations,
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
        COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
        COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
        COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
        COALESCE(SUM(os.nombre_secourues), 0)::INTEGER AS total_secourues,
        COALESCE(SUM(os.nombre_assistees), 0)::INTEGER AS total_assistees,
        COALESCE(SUM(os.nombre_retrouvees), 0)::INTEGER AS total_retrouvees,
        COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
        COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
        COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
        MIN(o.date_heure_reception_alerte)::DATE AS premiere_operation,
        MAX(o.date_heure_reception_alerte)::DATE AS derniere_operation,
        EXTRACT(DAY FROM MAX(o.date_heure_reception_alerte) - MIN(o.date_heure_reception_alerte)) + 1 AS jours_activite
    FROM operations o
    LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
    WHERE o."cross" IS NOT NULL
        AND o.date_heure_reception_alerte IS NOT NULL
    GROUP BY o."cross"
)
SELECT
    cross_name,
    nb_operations,
    ROUND(duree_moyenne_heures::NUMERIC, 2) AS duree_moyenne_heures,
    ROUND(duree_mediane_heures::NUMERIC, 2) AS duree_mediane_heures,
    ROUND(duree_min_heures::NUMERIC, 2) AS duree_min_heures,
    ROUND(duree_max_heures::NUMERIC, 2) AS duree_max_heures,
    total_saines_sauves,
    total_prises_en_compte,
    ROUND(
        total_saines_sauves::NUMERIC / NULLIF(total_prises_en_compte, 0) * 100, 2
    ) AS taux_saines_sauves,
    total_personnes,
    total_secourues,
    total_assistees,
    total_retrouvees,
    total_decedes,
    total_disparus,
    total_blesses,
    ROUND(
        total_decedes::NUMERIC / NULLIF(total_prises_en_compte, 0) * 100, 2
    ) AS taux_mortalite,
    ROUND(
        nb_operations::NUMERIC / NULLIF(jours_activite, 0), 2
    ) AS operations_par_jour,
    ROUND(
        total_personnes::NUMERIC / NULLIF(nb_operations, 0), 2
    ) AS personnes_par_operation,
    RANK() OVER (ORDER BY nb_operations DESC) AS rank_volume,
    RANK() OVER (
        ORDER BY total_saines_sauves::NUMERIC / NULLIF(total_prises_en_compte, 0) DESC NULLS LAST
    ) AS rank_sauvetage,
    RANK() OVER (ORDER BY duree_mediane_heures ASC NULLS LAST) AS rank_rapidite,
    premiere_operation,
    derniere_operation
FROM cross_stats
ORDER BY nb_operations DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_cross_benchmark_mv_pk ON v_kpi_cross_benchmark_mv(cross_name);

-- =============================================================================
-- Vue matérialisée Flotteurs par catégorie (évite JOIN 3 tables)
-- =============================================================================
-- OBJECTIF: Pré-calculer les stats par catégorie de flotteur
-- GAIN: ~2-3s → 10ms (99% plus rapide)
-- REFRESH: Après chaque ETL
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_flotteurs_categorie_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_flotteurs_categorie_mv AS
SELECT
    f.categorie_flotteur,
    COUNT(DISTINCT f.operation_id)::INTEGER as total_operations,
    COUNT(*)::INTEGER as total_flotteurs,
    COALESCE(SUM(s.nombre_impliques), 0)::INTEGER as total_personnes,
    COALESCE(SUM(s.nombre_saines_sauves), 0)::INTEGER as total_saines_sauves,
    COALESCE(SUM(s.nombre_decedes), 0)::INTEGER as total_decedes,
    COALESCE(SUM(s.nombre_prises_en_compte), 0)::INTEGER as total_prises_en_compte,
    ROUND(COALESCE(SUM(s.nombre_saines_sauves), 0)::NUMERIC /
          NULLIF(SUM(s.nombre_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
    ROUND(COALESCE(SUM(s.nombre_decedes), 0)::NUMERIC /
          NULLIF(SUM(s.nombre_prises_en_compte), 0) * 100, 2) as taux_mortalite,
    ROUND(AVG(o.distance_cote_metres)::NUMERIC, 0) as distance_cote_moyenne_m
FROM flotteurs f
JOIN operations o ON f.operation_id = o.operation_id
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE f.categorie_flotteur IS NOT NULL
GROUP BY f.categorie_flotteur
ORDER BY total_operations DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_flotteurs_categorie_mv_pk ON v_kpi_flotteurs_categorie_mv(categorie_flotteur);

-- =============================================================================
-- Vue matérialisée Flotteurs par catégorie (CROSS actifs)
-- =============================================================================
-- OBJECTIF: Pré-calculer les stats par catégorie pour les CROSS actifs
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_flotteurs_categorie_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_flotteurs_categorie_cross_actifs_mv AS
SELECT
    f.categorie_flotteur,
    COUNT(DISTINCT f.operation_id)::INTEGER as total_operations,
    COUNT(*)::INTEGER as total_flotteurs,
    COALESCE(SUM(s.nombre_impliques), 0)::INTEGER as total_personnes,
    COALESCE(SUM(s.nombre_saines_sauves), 0)::INTEGER as total_saines_sauves,
    COALESCE(SUM(s.nombre_decedes), 0)::INTEGER as total_decedes,
    COALESCE(SUM(s.nombre_prises_en_compte), 0)::INTEGER as total_prises_en_compte,
    ROUND(COALESCE(SUM(s.nombre_saines_sauves), 0)::NUMERIC /
          NULLIF(SUM(s.nombre_prises_en_compte), 0) * 100, 2) as taux_saines_sauves,
    ROUND(COALESCE(SUM(s.nombre_decedes), 0)::NUMERIC /
          NULLIF(SUM(s.nombre_prises_en_compte), 0) * 100, 2) as taux_mortalite,
    ROUND(AVG(o.distance_cote_metres)::NUMERIC, 0) as distance_cote_moyenne_m
FROM flotteurs f
JOIN operations o ON f.operation_id = o.operation_id
JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
WHERE f.categorie_flotteur IS NOT NULL
GROUP BY f.categorie_flotteur
ORDER BY total_operations DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_flotteurs_categorie_cross_actifs_mv_pk
ON v_kpi_flotteurs_categorie_cross_actifs_mv(categorie_flotteur);

-- =============================================================================
-- Vue matérialisée Flotteurs détaillés (CROSS actifs)
-- =============================================================================
-- OBJECTIF: Pré-calculer les stats par type/catégorie/résultat pour CROSS actifs
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_flotteurs_analyse_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_flotteurs_analyse_cross_actifs_mv AS
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
JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE f.categorie_flotteur IS NOT NULL
GROUP BY f.type_flotteur, f.categorie_flotteur, f.resultat_flotteur
ORDER BY nb_operations DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_flotteurs_analyse_cross_actifs_mv_pk
ON v_kpi_flotteurs_analyse_cross_actifs_mv(
    type_flotteur,
    categorie_flotteur,
    resultat_flotteur
);

-- =============================================================================
-- Vue matérialisée Alertes & Anomalies (évite CTE + fenêtres mobiles 12 mois)
-- =============================================================================
-- OBJECTIF: Pré-calculer les z-scores et alertes mensuels
-- GAIN: ~2-5s → 10ms (99% plus rapide)
-- REFRESH: Après chaque ETL
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_alertes_anomalies_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_alertes_anomalies_mv AS
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
    ROUND((m.nb_operations - sr.moy_operations)::NUMERIC, 2) AS ecart_operations,
    ROUND((m.total_personnes - sr.moy_personnes)::NUMERIC, 2) AS ecart_personnes,
    ROUND((m.total_victimes - sr.moy_victimes)::NUMERIC, 2) AS ecart_victimes,
    ROUND((m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0), 2) AS zscore_operations,
    ROUND((m.total_personnes - sr.moy_personnes) / NULLIF(sr.std_personnes, 0), 2) AS zscore_personnes,
    ROUND((m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0), 2) AS zscore_victimes,
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
    ROUND(sr.moy_operations::NUMERIC, 2) AS moyenne_operations,
    ROUND(sr.moy_personnes::NUMERIC, 2) AS moyenne_personnes,
    ROUND(sr.moy_victimes::NUMERIC, 2) AS moyenne_victimes
FROM monthly_stats m
LEFT JOIN stats_rolling sr ON m.periode = sr.periode
ORDER BY m.periode DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_alertes_anomalies_mv_pk ON v_kpi_alertes_anomalies_mv(periode);

-- =============================================================================
-- Vue matérialisée Alertes & Anomalies (CROSS actifs)
-- =============================================================================
-- OBJECTIF: Pré-calculer les z-scores pour les CROSS actifs
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_alertes_anomalies_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_alertes_anomalies_cross_actifs_mv AS
WITH monthly_stats AS (
    SELECT
        DATE_TRUNC('month', o.date_heure_reception_alerte)::DATE AS periode,
        COUNT(*)::INTEGER AS nb_operations,
        COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
        COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
        COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
        COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes
    FROM operations o
    JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
    LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
    WHERE o.date_heure_reception_alerte IS NOT NULL
    GROUP BY DATE_TRUNC('month', o.date_heure_reception_alerte)
),
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
    ROUND((m.nb_operations - sr.moy_operations)::NUMERIC, 2) AS ecart_operations,
    ROUND((m.total_personnes - sr.moy_personnes)::NUMERIC, 2) AS ecart_personnes,
    ROUND((m.total_victimes - sr.moy_victimes)::NUMERIC, 2) AS ecart_victimes,
    ROUND((m.nb_operations - sr.moy_operations) / NULLIF(sr.std_operations, 0), 2) AS zscore_operations,
    ROUND((m.total_personnes - sr.moy_personnes) / NULLIF(sr.std_personnes, 0), 2) AS zscore_personnes,
    ROUND((m.total_victimes - sr.moy_victimes) / NULLIF(sr.std_victimes, 0), 2) AS zscore_victimes,
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
    ROUND(sr.moy_operations::NUMERIC, 2) AS moyenne_operations,
    ROUND(sr.moy_personnes::NUMERIC, 2) AS moyenne_personnes,
    ROUND(sr.moy_victimes::NUMERIC, 2) AS moyenne_victimes
FROM monthly_stats m
LEFT JOIN stats_rolling sr ON m.periode = sr.periode
ORDER BY m.periode DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_alertes_anomalies_cross_actifs_mv_pk
ON v_kpi_alertes_anomalies_cross_actifs_mv(periode);

-- =============================================================================
-- Vue matérialisée Sécurité Mensuelle (évite agrégations complexes)
-- =============================================================================
-- OBJECTIF: Pré-calculer les KPIs de sécurité mensuels
-- GAIN: ~500ms → 10ms (98% plus rapide)
-- REFRESH: Après chaque ETL
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_securite_mensuel_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_securite_mensuel_mv AS
SELECT
    DATE_TRUNC('month', o.date_heure_reception_alerte)::DATE AS periode,
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
    EXTRACT(MONTH FROM o.date_heure_reception_alerte)::INTEGER AS mois,
    COUNT(*)::INTEGER AS nb_operations,
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_impliques,
    COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
    COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
    COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
    COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
    COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
    COALESCE(SUM(os.nombre_secourues), 0)::INTEGER AS total_secourues,
    COALESCE(SUM(os.nombre_assistees), 0)::INTEGER AS total_assistees,
    COALESCE(SUM(os.nombre_retrouvees), 0)::INTEGER AS total_retrouvees,
    COALESCE(SUM(os.nombre_tirees_affaire_seule), 0)::INTEGER AS total_tirees_affaire_seule,
    COALESCE(SUM(os.nombre_fausses_alertes), 0)::INTEGER AS total_fausses_alertes,
    ROUND(COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_saines_sauves,
    ROUND(COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_mortalite,
    ROUND(COALESCE(SUM(os.nombre_disparus), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_disparition,
    ROUND(COALESCE(SUM(os.nombre_blesses), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_blessure,
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

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_securite_mensuel_mv_pk ON v_kpi_securite_mensuel_mv(periode);

-- =============================================================================
-- Vue matérialisée Sécurité Mensuelle (CROSS actifs)
-- =============================================================================
-- OBJECTIF: Pré-calculer les KPIs mensuels pour les CROSS actifs
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_securite_mensuel_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_securite_mensuel_cross_actifs_mv AS
SELECT
    DATE_TRUNC('month', o.date_heure_reception_alerte)::DATE AS periode,
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
    EXTRACT(MONTH FROM o.date_heure_reception_alerte)::INTEGER AS mois,
    COUNT(*)::INTEGER AS nb_operations,
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_impliques,
    COALESCE(SUM(os.nombre_saines_sauves), 0)::INTEGER AS total_saines_sauves,
    COALESCE(SUM(os.nombre_prises_en_compte), 0)::INTEGER AS total_prises_en_compte,
    COALESCE(SUM(os.nombre_decedes), 0)::INTEGER AS total_decedes,
    COALESCE(SUM(os.nombre_disparus), 0)::INTEGER AS total_disparus,
    COALESCE(SUM(os.nombre_blesses), 0)::INTEGER AS total_blesses,
    COALESCE(SUM(os.nombre_secourues), 0)::INTEGER AS total_secourues,
    COALESCE(SUM(os.nombre_assistees), 0)::INTEGER AS total_assistees,
    COALESCE(SUM(os.nombre_retrouvees), 0)::INTEGER AS total_retrouvees,
    COALESCE(SUM(os.nombre_tirees_affaire_seule), 0)::INTEGER AS total_tirees_affaire_seule,
    COALESCE(SUM(os.nombre_fausses_alertes), 0)::INTEGER AS total_fausses_alertes,
    ROUND(COALESCE(SUM(os.nombre_saines_sauves), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_saines_sauves,
    ROUND(COALESCE(SUM(os.nombre_decedes), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_mortalite,
    ROUND(COALESCE(SUM(os.nombre_disparus), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_disparition,
    ROUND(COALESCE(SUM(os.nombre_blesses), 0)::NUMERIC /
          NULLIF(SUM(os.nombre_prises_en_compte), 0) * 100, 2) AS taux_blessure,
    ROUND(
        (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
         COALESCE(SUM(os.nombre_disparus), 0) * 2 +
         COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
    ) AS indice_gravite
FROM operations o
JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY DATE_TRUNC('month', o.date_heure_reception_alerte),
         EXTRACT(YEAR FROM o.date_heure_reception_alerte),
         EXTRACT(MONTH FROM o.date_heure_reception_alerte)
ORDER BY periode DESC;

-- Index unique requis pour REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_securite_mensuel_cross_actifs_mv_pk
ON v_kpi_securite_mensuel_cross_actifs_mv(periode);

-- =============================================================================
-- Vues matérialisées temporelles & météo (CROSS actifs)
-- =============================================================================
DROP MATERIALIZED VIEW IF EXISTS v_kpi_saisonnalite_mensuelle_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_saisonnalite_mensuelle_cross_actifs_mv AS
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
    EXTRACT(MONTH FROM o.date_heure_reception_alerte)::INTEGER AS mois,
    COUNT(*)::INTEGER AS nb_operations,
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
    COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
    ROUND(
        (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
         COALESCE(SUM(os.nombre_disparus), 0) * 2 +
         COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
    ) AS indice_gravite_moyen
FROM operations o
JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE o.date_heure_reception_alerte IS NOT NULL
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte),
         EXTRACT(MONTH FROM o.date_heure_reception_alerte)
ORDER BY annee DESC, mois;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_saisonnalite_mensuelle_cross_actifs_mv_pk
ON v_kpi_saisonnalite_mensuelle_cross_actifs_mv(annee, mois);

DROP MATERIALIZED VIEW IF EXISTS v_kpi_phase_journee_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_phase_journee_cross_actifs_mv AS
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
    o.phase_journee,
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
JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE o.phase_journee IS NOT NULL
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte), o.phase_journee
ORDER BY annee DESC, total_operations DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_phase_journee_cross_actifs_mv_pk
ON v_kpi_phase_journee_cross_actifs_mv(annee, phase_journee);

DROP MATERIALIZED VIEW IF EXISTS v_kpi_impact_vacances_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_impact_vacances_cross_actifs_mv AS
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
    o.est_vacances_scolaires AS en_vacances,
    COUNT(*)::INTEGER AS total_operations,
    COALESCE(SUM(os.nombre_impliques), 0)::INTEGER AS total_personnes,
    COALESCE(SUM(os.nombre_decedes + os.nombre_disparus), 0)::INTEGER AS total_victimes,
    ROUND(AVG(os.nombre_impliques)::NUMERIC, 2) AS moy_personnes_par_op,
    ROUND(
        (COALESCE(SUM(os.nombre_decedes), 0) * 3 +
         COALESCE(SUM(os.nombre_disparus), 0) * 2 +
         COALESCE(SUM(os.nombre_blesses), 0))::NUMERIC /
        NULLIF(SUM(os.nombre_prises_en_compte), 0), 3
    ) AS indice_gravite_moyen
FROM operations o
JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE o.est_vacances_scolaires IS NOT NULL
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte), o.est_vacances_scolaires
ORDER BY annee DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_impact_vacances_cross_actifs_mv_pk
ON v_kpi_impact_vacances_cross_actifs_mv(annee, en_vacances);

DROP MATERIALIZED VIEW IF EXISTS v_kpi_meteo_correlation_cross_actifs_mv CASCADE;

CREATE MATERIALIZED VIEW v_kpi_meteo_correlation_cross_actifs_mv AS
SELECT
    EXTRACT(YEAR FROM o.date_heure_reception_alerte)::INTEGER AS annee,
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
JOIN v_cross_actifs ca ON o."cross" = ca.cross_name
LEFT JOIN operations_stats os ON o.operation_id = os.operation_id
WHERE (o.vent_force IS NOT NULL OR o.mer_force IS NOT NULL)
GROUP BY EXTRACT(YEAR FROM o.date_heure_reception_alerte), o.vent_force, o.mer_force
ORDER BY annee DESC, nb_operations DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_v_kpi_meteo_correlation_cross_actifs_mv_pk
ON v_kpi_meteo_correlation_cross_actifs_mv(annee, vent_force, mer_force);

-- =============================================================================
-- Utilisateurs de test : créés via dev.py (hash bcrypt généré dynamiquement)
-- =============================================================================
-- Les utilisateurs admin/editor/viewer sont créés par la fonction create_test_users()
-- dans dev.py pour garantir des hashs bcrypt valides.

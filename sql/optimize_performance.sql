-- =============================================================================
-- Script d'optimisation des performances pour Render
-- =============================================================================
-- Ce script:
-- 1. Crée les index manquants
-- 2. Convertit operations_stats en VUE MATÉRIALISÉE
-- 3. Crée un index sur la vue matérialisée
--
-- Usage: psql $DATABASE_URL -f sql/optimize_performance.sql
-- =============================================================================

-- Définir le schéma
SET search_path TO clean;

-- =============================================================================
-- ÉTAPE 1: Créer les index s'ils n'existent pas
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_operations_date ON operations(date_heure_reception_alerte);
CREATE INDEX IF NOT EXISTS idx_operations_cross ON operations("cross");
CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(type_operation);
CREATE INDEX IF NOT EXISTS idx_operations_prefecture ON operations(prefecture_maritime);
CREATE INDEX IF NOT EXISTS idx_flotteurs_operation ON flotteurs(operation_id);
CREATE INDEX IF NOT EXISTS idx_resultats_operation ON resultats_humain(operation_id);
CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);

-- Index composite pour les requêtes courantes (CROSS + date)
CREATE INDEX IF NOT EXISTS idx_operations_cross_date
ON operations("cross", date_heure_reception_alerte);

-- Index pour les agrégations par année
CREATE INDEX IF NOT EXISTS idx_operations_year
ON operations(EXTRACT(YEAR FROM date_heure_reception_alerte));

-- =============================================================================
-- ÉTAPE 2: Supprimer l'ancienne VIEW et créer une MATERIALIZED VIEW
-- =============================================================================

-- Supprimer l'ancienne vue
DROP VIEW IF EXISTS operations_stats CASCADE;

-- Créer la vue matérialisée (pré-calculée, stockée sur disque)
CREATE MATERIALIZED VIEW IF NOT EXISTS operations_stats AS
SELECT
    o.operation_id,

    -- MÉTRIQUES OFFICIELLES SECMAR
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN (
            'Personne secourue',
            'Personne assistée',
            'Personne retrouvée'
        )
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_saines_sauves,

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

    -- MÉTRIQUES DÉTAILLÉES
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN (
            'Personne décédée',
            'Personne décédée accidentellement',
            'Personne décédée naturellement'
        )
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_decedes,

    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne disparue'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_disparus,

    COALESCE(SUM(COALESCE(rh.dont_nombre_blesse, 0)), 0)::INTEGER as nombre_blesses,

    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne secourue'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_secourues,

    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne assistée'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_assistees,

    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne retrouvée'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_retrouvees,

    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne tirée d''affaire seule'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_tirees_affaire_seule,

    COALESCE(SUM(rh.nombre), 0)::INTEGER as nombre_impliques,

    COALESCE(SUM(CASE
        WHEN rh.resultat_humain = 'Personne impliquée dans fausse alerte'
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_fausses_alertes

FROM operations o
LEFT JOIN resultats_humain rh ON o.operation_id = rh.operation_id
GROUP BY o.operation_id;

-- Index sur la vue matérialisée pour les jointures rapides
CREATE UNIQUE INDEX IF NOT EXISTS idx_ops_stats_operation_id
ON operations_stats(operation_id);

-- =============================================================================
-- ÉTAPE 3: Mettre à jour les statistiques PostgreSQL
-- =============================================================================
ANALYZE operations;
ANALYZE resultats_humain;
ANALYZE flotteurs;
ANALYZE operations_stats;

-- =============================================================================
-- AFFICHER LE RÉSULTAT
-- =============================================================================
SELECT 'Optimisation terminée!' as status;
SELECT
    'operations_stats' as view_name,
    CASE
        WHEN EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = 'operations_stats' AND schemaname = 'clean')
        THEN 'MATERIALIZED VIEW (optimisée)'
        ELSE 'ERREUR: Vue non créée'
    END as view_type;

-- =============================================================================
-- Script de diagnostic des index et performances
-- =============================================================================
-- Usage: Exécuter sur Render pour vérifier l'état des index
-- psql $DATABASE_URL -f sql/check_indexes.sql
-- =============================================================================

-- Définir le schéma
SET search_path TO clean;

-- 1. Vérifier les index existants
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'clean'
ORDER BY tablename, indexname;

-- 2. Compter les lignes dans chaque table
SELECT 'operations' as table_name, COUNT(*) as row_count FROM operations
UNION ALL
SELECT 'resultats_humain', COUNT(*) FROM resultats_humain
UNION ALL
SELECT 'flotteurs', COUNT(*) FROM flotteurs;

-- 3. Analyser la taille des tables
SELECT
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size,
    pg_size_pretty(pg_relation_size(relid)) as table_size,
    pg_size_pretty(pg_indexes_size(relid)) as index_size
FROM pg_catalog.pg_statio_user_tables
WHERE schemaname = 'clean'
ORDER BY pg_total_relation_size(relid) DESC;

-- 4. Vérifier si la vue operations_stats est une vue normale ou matérialisée
SELECT
    'operations_stats' as view_name,
    CASE
        WHEN EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = 'operations_stats' AND schemaname = 'clean')
        THEN 'MATERIALIZED VIEW'
        ELSE 'REGULAR VIEW (recalculée à chaque requête)'
    END as view_type;

-- 5. EXPLAIN ANALYZE sur une requête typique (commenté par défaut car long)
-- EXPLAIN ANALYZE
-- SELECT COUNT(*), SUM(s.nombre_impliques)
-- FROM operations o
-- LEFT JOIN operations_stats s ON o.operation_id = s.operation_id
-- WHERE o."cross" IN ('Corsen', 'Étel', 'Jobourg');

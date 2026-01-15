-- =============================================================================
-- Script de rafraîchissement des vues matérialisées
-- =============================================================================
-- À exécuter après chaque chargement de données (ETL)
-- Usage: psql $DATABASE_URL -f sql/refresh_materialized_views.sql
-- =============================================================================

SET search_path TO clean;

-- 1. operations_stats (source pour les autres vues)
REFRESH MATERIALIZED VIEW CONCURRENTLY operations_stats;
ANALYZE operations_stats;

-- 2. v_kpi_global (KPIs globaux)
REFRESH MATERIALIZED VIEW v_kpi_global;

-- 3. v_kpi_annuel (stats annuelles)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_annuel;

-- 4. v_kpi_cross (stats par CROSS)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_cross;

-- 5. v_kpi_yoy_cross_actifs (Year-over-Year pour CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_yoy_cross_actifs;

-- 6. v_kpi_cross_benchmark_mv (Performance CROSS - Phase 4)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_cross_benchmark_mv;

-- 7. v_kpi_flotteurs_categorie_mv (Flotteurs par catégorie - Phase 4)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_flotteurs_categorie_mv;

-- 8. v_kpi_flotteurs_categorie_cross_actifs_mv (Flotteurs catégorie - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_flotteurs_categorie_cross_actifs_mv;

-- 9. v_kpi_flotteurs_analyse_cross_actifs_mv (Flotteurs détaillés - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_flotteurs_analyse_cross_actifs_mv;

-- 10. v_kpi_alertes_anomalies_mv (Alertes et anomalies avec z-scores)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_alertes_anomalies_mv;

-- 11. v_kpi_alertes_anomalies_cross_actifs_mv (Alertes - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_alertes_anomalies_cross_actifs_mv;

-- 12. v_kpi_securite_mensuel_mv (Sécurité mensuelle)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_securite_mensuel_mv;

-- 13. v_kpi_securite_mensuel_cross_actifs_mv (Sécurité - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_securite_mensuel_cross_actifs_mv;

-- 14. v_kpi_saisonnalite_mensuelle_cross_actifs_mv (Saisonnalité - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_saisonnalite_mensuelle_cross_actifs_mv;

-- 15. v_kpi_phase_journee_cross_actifs_mv (Phase journee - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_phase_journee_cross_actifs_mv;

-- 16. v_kpi_impact_vacances_cross_actifs_mv (Vacances - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_impact_vacances_cross_actifs_mv;

-- 17. v_kpi_meteo_correlation_cross_actifs_mv (Meteo - CROSS actifs)
REFRESH MATERIALIZED VIEW CONCURRENTLY v_kpi_meteo_correlation_cross_actifs_mv;

SELECT 'Vues matérialisées rafraîchies!' as status,
       COUNT(*) as operations_count
FROM operations_stats;

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

-- =============================================================================
-- VIEW operations_stats (calculée automatiquement depuis resultats_humain)
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
-- =============================================================================
DROP VIEW IF EXISTS operations_stats CASCADE;

CREATE OR REPLACE VIEW operations_stats AS
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
-- Utilisateurs de test : créés via dev.py (hash bcrypt généré dynamiquement)
-- =============================================================================
-- Les utilisateurs admin/editor/viewer sont créés par la fonction create_test_users()
-- dans dev.py pour garantir des hashs bcrypt valides.

-- =============================================================================
-- Vérification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '=== Tables MCD créées avec succès ===';
    RAISE NOTICE 'Operations: %', (SELECT COUNT(*) FROM operations);
    RAISE NOTICE 'Flotteurs: %', (SELECT COUNT(*) FROM flotteurs);
    RAISE NOTICE 'Resultats: %', (SELECT COUNT(*) FROM resultats_humain);
    RAISE NOTICE 'Users: %', (SELECT COUNT(*) FROM users);
    RAISE NOTICE 'Stats (VIEW): %', (SELECT COUNT(*) FROM operations_stats);
    RAISE NOTICE '';
    RAISE NOTICE 'Utilisateurs de test:';
    RAISE NOTICE '  - admin / admin123 (role: admin)';
    RAISE NOTICE '  - editor / editor123 (role: editor)';
    RAISE NOTICE '  - viewer / viewer123 (role: viewer)';
END $$;

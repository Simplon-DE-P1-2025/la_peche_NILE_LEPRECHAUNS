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
    operation_id INTEGER PRIMARY KEY,
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
    departement VARCHAR(3),
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
    operation_id INTEGER NOT NULL REFERENCES operations(operation_id) ON DELETE CASCADE,
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
    operation_id INTEGER NOT NULL REFERENCES operations(operation_id) ON DELETE CASCADE,
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
    operation_type VARCHAR(10) NOT NULL CHECK (operation_type IN ('INSERT', 'UPDATE', 'DELETE')),
    record_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    user_id VARCHAR(50) DEFAULT 'system',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



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
-- Trigger d'audit (sans operations_stats qui est une VIEW)
-- =============================================================================
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    record_pk INTEGER;
    old_json JSONB;
    new_json JSONB;
BEGIN
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

    IF TG_OP = 'INSERT' THEN
        new_json := to_jsonb(NEW);
        INSERT INTO audit_log (table_name, operation_type, record_id, new_values, user_id)
        VALUES (TG_TABLE_NAME, 'INSERT', record_pk, new_json,
                COALESCE(current_setting('app.current_user', true), 'system'));
    ELSIF TG_OP = 'UPDATE' THEN
        old_json := to_jsonb(OLD);
        new_json := to_jsonb(NEW);
        INSERT INTO audit_log (table_name, operation_type, record_id, old_values, new_values, user_id)
        VALUES (TG_TABLE_NAME, 'UPDATE', record_pk, old_json, new_json,
                COALESCE(current_setting('app.current_user', true), 'system'));
    ELSIF TG_OP = 'DELETE' THEN
        old_json := to_jsonb(OLD);
        INSERT INTO audit_log (table_name, operation_type, record_id, old_values, user_id)
        VALUES (TG_TABLE_NAME, 'DELETE', record_pk, old_json,
                COALESCE(current_setting('app.current_user', true), 'system'));
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



-- =============================================================================
-- STUB Tables - Alignées avec le MCD SECMAR
-- =============================================================================
-- Ce script crée les tables pour le développement CRUD et Streamlit.
-- Aligné avec le MCD (source de vérité) + documentation SECMAR officielle.
--
-- Usage: psql -d secmar_db -f sql/stub_tables.sql
-- =============================================================================

-- Table des opérations (enrichie avec champs MCD)
CREATE TABLE IF NOT EXISTS operations (
    operation_id INTEGER PRIMARY KEY,
    numero_sitrep VARCHAR(50),
    date_operation DATE,
    heure_operation TIME,
    type_operation VARCHAR(100),
    sous_type_operation VARCHAR(100),
    "cross" VARCHAR(50),
    departement VARCHAR(3),
    zone_responsabilite VARCHAR(50),
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    vent_direction INTEGER,
    vent_force INTEGER,
    mer_force INTEGER,
    meteo VARCHAR(100),
    nombre_personnes_impliquees INTEGER DEFAULT 0,
    nombre_moyens_engages INTEGER DEFAULT 0,
    duree_intervention INTEGER,
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
    immatriculation VARCHAR(50),
    nom_flotteur VARCHAR(100),
    longueur DECIMAL(6, 2),
    nombre_personnes INTEGER DEFAULT 0,
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
-- VIEW operations_stats (calculée automatiquement depuis resultats_humain)
-- =============================================================================
DROP VIEW IF EXISTS operations_stats CASCADE;

CREATE OR REPLACE VIEW operations_stats AS
SELECT
    o.operation_id,
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN ('Personne decedee', 'Decede', 'Décédé')
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_decedes,
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN ('Personne disparue', 'Disparu')
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_disparus,
    COALESCE(SUM(COALESCE(rh.dont_nombre_blesse, 0)), 0)::INTEGER +
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN ('Blesse', 'Blessé')
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_blesses,
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN ('Personne secourue', 'Sain et sauf', 'Retrouve', 'Personne retrouvee')
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_sauves,
    COALESCE(SUM(rh.nombre), 0)::INTEGER as nombre_impliques,
    COALESCE(SUM(CASE
        WHEN rh.resultat_humain IN ('Personne assistee', 'Assiste')
        THEN rh.nombre ELSE 0
    END), 0)::INTEGER as nombre_assistances
FROM operations o
LEFT JOIN resultats_humain rh ON o.operation_id = rh.operation_id
GROUP BY o.operation_id;

-- =============================================================================
-- Index pour les performances
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_operations_date ON operations(date_operation);
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

-- =============================================================================
-- Données de test
-- =============================================================================

-- Utilisateurs de test
INSERT INTO users (username, email, password_hash, role)
VALUES
    ('admin', 'admin@secmar.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYF/mHKLqHCi', 'admin'),
    ('editor', 'editor@secmar.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYF/mHKLqHCi', 'editor'),
    ('viewer', 'viewer@secmar.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYF/mHKLqHCi', 'viewer')
ON CONFLICT (username) DO NOTHING;

-- Opérations de test (avec champs enrichissement)
INSERT INTO operations (operation_id, numero_sitrep, date_operation, type_operation, "cross", departement,
    latitude, longitude, nombre_personnes_impliquees, duree_intervention,
    prefecture_maritime, phase_journee, distance_cote_metres)
VALUES
    (1, 'SITREP-2024-001', '2024-01-15', 'SAR', 'Etel', '56', 47.5000, -3.2000, 5, 120, 'Atlantique', 'Matin', 2500),
    (2, 'SITREP-2024-002', '2024-01-16', 'MAS', 'Corsen', '29', 48.4500, -4.7500, 3, 90, 'Atlantique', 'Apres-midi', 5000),
    (3, 'SITREP-2024-003', '2024-01-17', 'DIV', 'Jobourg', '50', 49.6800, -1.9000, 2, 45, 'Manche et mer du Nord', 'Matin', 1200),
    (4, 'SITREP-2024-004', '2024-01-18', 'SAR', 'La Garde', '83', 43.1000, 5.9300, 8, 180, 'Mediterranee', 'Soir', 8000),
    (5, 'SITREP-2024-005', '2024-01-19', 'SUR', 'Gris-Nez', '62', 50.8700, 1.5800, 4, 60, 'Manche et mer du Nord', 'Nuit', 3500)
ON CONFLICT (operation_id) DO NOTHING;

-- Flotteurs de test (avec numero_ordre)
INSERT INTO flotteurs (operation_id, numero_ordre, type_flotteur, categorie_flotteur, pavillon, longueur, nombre_personnes)
VALUES
    (1, 1, 'Plaisance a voile', 'Plaisance', 'France', 12.50, 3),
    (1, 2, 'Annexe', 'Secours', 'France', 5.00, 2),
    (2, 1, 'Peche', 'Pêche', 'France', 18.00, 5),
    (3, 1, 'Canoe/Kayak', 'Loisir nautique', 'France', 4.00, 1),
    (4, 1, 'Plaisance a moteur', 'Plaisance', 'Monaco', 25.00, 8)
ON CONFLICT DO NOTHING;

-- Résultats humains de test (avec dont_nombre_blesse)
INSERT INTO resultats_humain (operation_id, categorie_personne, resultat_humain, nombre, dont_nombre_blesse)
VALUES
    (1, 'Equipage', 'Sain et sauf', 3, 0),
    (1, 'Passager', 'Sain et sauf', 2, 0),
    (2, 'Equipage', 'Sain et sauf', 4, 1),
    (3, 'Autre', 'Sain et sauf', 2, 0),
    (4, 'Passager', 'Sain et sauf', 6, 0),
    (4, 'Equipage', 'Sain et sauf', 2, 2)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Vérification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '=== Tables MCD créées avec succès ===';
    RAISE NOTICE 'Operations: %', (SELECT COUNT(*) FROM operations);
    RAISE NOTICE 'Flotteurs: %', (SELECT COUNT(*) FROM flotteurs);
    RAISE NOTICE 'Resultats: %', (SELECT COUNT(*) FROM resultats_humain);
    RAISE NOTICE 'Stats (VIEW): %', (SELECT COUNT(*) FROM operations_stats);
    RAISE NOTICE '';
    RAISE NOTICE 'Utilisateurs de test:';
    RAISE NOTICE '  - admin / admin123 (role: admin)';
    RAISE NOTICE '  - editor / editor123 (role: editor)';
    RAISE NOTICE '  - viewer / viewer123 (role: viewer)';
END $$;

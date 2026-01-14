-- =============================================================================
-- STUB Tables - Pour développement CRUD et Steamlit
-- =============================================================================
-- Ce script crée les tables minimales pour permettre le développement
-- du CRUD et de l'interface Streamlit AVANT que le travail amont soit terminé.
--
-- Usage: psql -d secmar_db -f sql/stub_tables.sql
--
-- TODO: L'équipier doit remplacer par les scripts complets :
-- - 01_create_tables.sql
-- - 02_create_audit.sql
-- - 03_create_users.sql
-- =============================================================================

-- Table des opérations
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des flotteurs
CREATE TABLE IF NOT EXISTS flotteurs (
    flotteur_id SERIAL PRIMARY KEY,
    operation_id INTEGER NOT NULL REFERENCES operations(operation_id) ON DELETE CASCADE,
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

-- Table des résultats humains
CREATE TABLE IF NOT EXISTS resultats_humain (
    resultat_id SERIAL PRIMARY KEY,
    operation_id INTEGER NOT NULL REFERENCES operations(operation_id) ON DELETE CASCADE,
    categorie_personne VARCHAR(50),
    resultat_humain VARCHAR(50),
    nombre INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des statistiques
CREATE TABLE IF NOT EXISTS operations_stats (
    stat_id SERIAL PRIMARY KEY,
    operation_id INTEGER NOT NULL REFERENCES operations(operation_id) ON DELETE CASCADE,
    nombre_decedes INTEGER DEFAULT 0,
    nombre_disparus INTEGER DEFAULT 0,
    nombre_blesses INTEGER DEFAULT 0,
    nombre_sauves INTEGER DEFAULT 0,
    nombre_impliques INTEGER DEFAULT 0,
    nombre_assistances INTEGER DEFAULT 0,
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

-- Table d'audit (simplifiée pour le stub)
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
CREATE INDEX IF NOT EXISTS idx_operations_date ON operations(date_operation);
CREATE INDEX IF NOT EXISTS idx_operations_cross ON operations("cross");
CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(type_operation);
CREATE INDEX IF NOT EXISTS idx_flotteurs_operation ON flotteurs(operation_id);
CREATE INDEX IF NOT EXISTS idx_resultats_operation ON resultats_humain(operation_id);
CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);

-- =============================================================================
-- Trigger d'audit simplifié
-- =============================================================================
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    record_pk INTEGER;
    old_json JSONB;
    new_json JSONB;
BEGIN
    -- Déterminer la clé primaire
    CASE TG_TABLE_NAME
        WHEN 'operations' THEN
            record_pk := COALESCE(NEW.operation_id, OLD.operation_id);
        WHEN 'flotteurs' THEN
            record_pk := COALESCE(NEW.flotteur_id, OLD.flotteur_id);
        WHEN 'resultats_humain' THEN
            record_pk := COALESCE(NEW.resultat_id, OLD.resultat_id);
        WHEN 'operations_stats' THEN
            record_pk := COALESCE(NEW.stat_id, OLD.stat_id);
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

-- Créer les triggers
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

DROP TRIGGER IF EXISTS audit_operations_stats ON operations_stats;
CREATE TRIGGER audit_operations_stats
    AFTER INSERT OR UPDATE OR DELETE ON operations_stats
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- =============================================================================
-- Données de test
-- =============================================================================

-- Utilisateur admin (mot de passe: admin123)
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@secmar.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYF/mHKLqHCi', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Utilisateur editor (mot de passe: editor123)
INSERT INTO users (username, email, password_hash, role)
VALUES ('editor', 'editor@secmar.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYF/mHKLqHCi', 'editor')
ON CONFLICT (username) DO NOTHING;

-- Utilisateur viewer (mot de passe: viewer123)
INSERT INTO users (username, email, password_hash, role)
VALUES ('viewer', 'viewer@secmar.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYF/mHKLqHCi', 'viewer')
ON CONFLICT (username) DO NOTHING;

-- Opérations de test
INSERT INTO operations (operation_id, numero_sitrep, date_operation, type_operation, "cross", departement, latitude, longitude, nombre_personnes_impliquees, duree_intervention)
VALUES
    (1, 'SITREP-2024-001', '2024-01-15', 'SAR', 'Etel', '56', 47.5000, -3.2000, 5, 120),
    (2, 'SITREP-2024-002', '2024-01-16', 'MAS', 'Corsen', '29', 48.4500, -4.7500, 3, 90),
    (3, 'SITREP-2024-003', '2024-01-17', 'DIV', 'Jobourg', '50', 49.6800, -1.9000, 2, 45),
    (4, 'SITREP-2024-004', '2024-01-18', 'SAR', 'La Garde', '83', 43.1000, 5.9300, 8, 180),
    (5, 'SITREP-2024-005', '2024-01-19', 'ASS', 'Gris-Nez', '62', 50.8700, 1.5800, 4, 60),
    (6, 'SITREP-2024-006', '2024-01-20', 'SAR', 'Etel', '56', 47.6500, -3.4000, 6, 150),
    (7, 'SITREP-2024-007', '2024-01-21', 'MAS', 'Corse', '2A', 41.9200, 8.7400, 2, 30),
    (8, 'SITREP-2024-008', '2024-01-22', 'SAR', 'Corsen', '29', 48.3800, -4.6900, 10, 240),
    (9, 'SITREP-2024-009', '2024-01-23', 'DIV', 'Jobourg', '50', 49.7200, -1.8500, 1, 25),
    (10, 'SITREP-2024-010', '2024-01-24', 'SAR', 'La Garde', '13', 43.2800, 5.3700, 7, 200)
ON CONFLICT (operation_id) DO NOTHING;

-- Flotteurs de test
INSERT INTO flotteurs (operation_id, type_flotteur, categorie_flotteur, pavillon, longueur, nombre_personnes)
VALUES
    (1, 'Voilier', 'Plaisance', 'France', 12.50, 3),
    (1, 'Zodiac', 'Secours', 'France', 5.00, 2),
    (2, 'Chalutier', 'Pêche', 'France', 18.00, 5),
    (3, 'Kayak', 'Loisir', 'France', 4.00, 1),
    (4, 'Yacht', 'Plaisance', 'Monaco', 25.00, 8),
    (5, 'Cargo', 'Commerce', 'Panama', 150.00, 20),
    (6, 'Catamaran', 'Plaisance', 'France', 14.00, 4),
    (8, 'Ferry', 'Transport', 'France', 180.00, 500)
ON CONFLICT DO NOTHING;

-- Résultats humains de test
INSERT INTO resultats_humain (operation_id, categorie_personne, resultat_humain, nombre)
VALUES
    (1, 'Equipage', 'Sain et sauf', 3),
    (1, 'Passager', 'Sain et sauf', 2),
    (2, 'Equipage', 'Blessé', 1),
    (2, 'Equipage', 'Sain et sauf', 2),
    (3, 'Autre', 'Sain et sauf', 2),
    (4, 'Passager', 'Sain et sauf', 6),
    (4, 'Equipage', 'Blessé', 2),
    (8, 'Equipage', 'Décédé', 1),
    (8, 'Equipage', 'Sain et sauf', 9)
ON CONFLICT DO NOTHING;

-- Statistiques de test
INSERT INTO operations_stats (operation_id, nombre_sauves, nombre_blesses, nombre_decedes, nombre_disparus)
VALUES
    (1, 5, 0, 0, 0),
    (2, 2, 1, 0, 0),
    (3, 2, 0, 0, 0),
    (4, 6, 2, 0, 0),
    (5, 4, 0, 0, 0),
    (6, 6, 0, 0, 0),
    (7, 2, 0, 0, 0),
    (8, 9, 0, 1, 0),
    (9, 1, 0, 0, 0),
    (10, 7, 0, 0, 0)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Vérification
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '=== STUB Tables créées avec succès ===';
    RAISE NOTICE 'Operations: %', (SELECT COUNT(*) FROM operations);
    RAISE NOTICE 'Flotteurs: %', (SELECT COUNT(*) FROM flotteurs);
    RAISE NOTICE 'Resultats: %', (SELECT COUNT(*) FROM resultats_humain);
    RAISE NOTICE 'Users: %', (SELECT COUNT(*) FROM users);
    RAISE NOTICE '';
    RAISE NOTICE 'Utilisateurs de test:';
    RAISE NOTICE '  - admin / admin123 (role: admin)';
    RAISE NOTICE '  - editor / editor123 (role: editor)';
    RAISE NOTICE '  - viewer / viewer123 (role: viewer)';
END $$;

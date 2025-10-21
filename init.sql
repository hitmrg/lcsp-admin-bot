-- Initialisation de la base de données 

-- Créer le schéma si nécessaire
CREATE SCHEMA IF NOT EXISTS public;

-- Extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Optimisations
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Index pour performances
-- (Seront créés automatiquement par SQLAlchemy)

-- Permissions
GRANT ALL PRIVILEGES ON SCHEMA public TO lcsp_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lcsp_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lcsp_admin;

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Base de données LCSP_DB initialisée avec succès!';
END $$;
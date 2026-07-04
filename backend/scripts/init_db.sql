-- ==============================================================
-- MSME Financial Health Card — Database Initialization Script
-- Runs once on container start via docker-entrypoint-initdb.d/
-- ==============================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search on MSME names

-- Ensure the app user has the right permissions
-- (user already created by POSTGRES_USER env var)
GRANT ALL PRIVILEGES ON DATABASE msme_healthcard TO msme_app;
GRANT CREATE ON SCHEMA public TO msme_app;

-- Note: Table creation is handled by Alembic migrations (Phase 2)
-- This script only sets up extensions and grants.

\echo 'Database initialization complete.'

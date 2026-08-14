-- =============================================================================
-- InsightAPI Enterprise Multi-Tenant Data Isolation Blueprint
--
-- This script provides two alternative/complementary tenant isolation strategies:
--   Option A: PostgreSQL Row-Level Security (RLS) — Recommended (Zero Migration Overhead)
--   Option B: Dedicated Per-Tenant Schemas — Strongest Isolation (Air-Gapped Compliance)
-- =============================================================================

-- =============================================================================
-- OPTION A: PostgreSQL Row-Level Security (RLS) Policies
-- =============================================================================

-- 1. Enable Row-Level Security on all tenant-partitioned tables
ALTER TABLE IF EXISTS crawl_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS crawl_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS auth_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS verified_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tos_acceptances ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;

-- 2. Create Tenant Isolation Policies using session setting `app.current_user_id`

-- Crawl Sessions Policy
DROP POLICY IF EXISTS tenant_isolation_crawl_sessions ON crawl_sessions;
CREATE POLICY tenant_isolation_crawl_sessions ON crawl_sessions
    FOR ALL
    USING (
        user_id = NULLIF(current_setting('app.current_user_id', true), '')
        OR current_setting('app.current_user_tier', true) = 'ADMIN'
    )
    WITH CHECK (
        user_id = NULLIF(current_setting('app.current_user_id', true), '')
        OR current_setting('app.current_user_tier', true) = 'ADMIN'
    );

-- Crawl Snapshots Policy (Inherited via project_id / crawl ownership)
DROP POLICY IF EXISTS tenant_isolation_crawl_snapshots ON crawl_snapshots;
CREATE POLICY tenant_isolation_crawl_snapshots ON crawl_snapshots
    FOR ALL
    USING (
        project_id = NULLIF(current_setting('app.current_user_id', true), '')
        OR current_setting('app.current_user_tier', true) = 'ADMIN'
    );

-- Auth Profiles Policy (Encrypted login credentials)
DROP POLICY IF EXISTS tenant_isolation_auth_profiles ON auth_profiles;
CREATE POLICY tenant_isolation_auth_profiles ON auth_profiles
    FOR ALL
    USING (
        user_id = NULLIF(current_setting('app.current_user_id', true), '')
        OR current_setting('app.current_user_tier', true) = 'ADMIN'
    )
    WITH CHECK (
        user_id = NULLIF(current_setting('app.current_user_id', true), '')
        OR current_setting('app.current_user_tier', true) = 'ADMIN'
    );

-- Verified Domains Policy
DROP POLICY IF EXISTS tenant_isolation_verified_domains ON verified_domains;
CREATE POLICY tenant_isolation_verified_domains ON verified_domains
    FOR ALL
    USING (
        user_id = NULLIF(current_setting('app.current_user_id', true), '')
        OR current_setting('app.current_user_tier', true) = 'ADMIN'
    );

-- Audit Logs Policy
DROP POLICY IF EXISTS tenant_isolation_audit_logs ON audit_logs;
CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    FOR ALL
    USING (
        user_id = NULLIF(current_setting('app.current_user_id', true), '')
        OR current_setting('app.current_user_tier', true) = 'ADMIN'
    );

-- 3. Application Connection Setup Pattern (Executed at start of each AsyncSession):
--    SET LOCAL app.current_user_id = 'usr_tenant_12345';
--    SET LOCAL app.current_user_tier = 'ENTERPRISE';


-- =============================================================================
-- OPTION B: Dedicated Per-Tenant PostgreSQL Schema Architecture
-- =============================================================================

-- Function to provision an isolated tenant namespace schema on-demand
CREATE OR REPLACE FUNCTION create_tenant_schema(p_tenant_id TEXT)
RETURNS VOID AS $$
DECLARE
    v_schema_name TEXT := 'tenant_' || lower(regexp_replace(p_tenant_id, '[^a-zA-Z0-9_]', '_', 'g'));
BEGIN
    -- 1. Create dedicated isolated schema
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', v_schema_name);

    -- 2. Clone tenant-isolated tables into the dedicated schema
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.crawl_sessions (LIKE public.crawl_sessions INCLUDING ALL);
        CREATE TABLE IF NOT EXISTS %I.crawl_snapshots (LIKE public.crawl_snapshots INCLUDING ALL);
        CREATE TABLE IF NOT EXISTS %I.auth_profiles (LIKE public.auth_profiles INCLUDING ALL);
        CREATE TABLE IF NOT EXISTS %I.audit_logs (LIKE public.audit_logs INCLUDING ALL);
    ', v_schema_name, v_schema_name, v_schema_name, v_schema_name);

    RAISE NOTICE 'Provisioned dedicated tenant schema: %', v_schema_name;
END;
$$ LANGUAGE plpgsql;

-- To switch connection context to a tenant's schema:
-- SET search_path TO tenant_cust123, public;

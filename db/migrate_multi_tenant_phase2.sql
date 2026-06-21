-- Phase 2: onboarding schema — organization handles, roles, invitation ledgers.

-- agencies: organization_handle + subscription_state
ALTER TABLE agencies ADD COLUMN organization_handle VARCHAR(50) NULL AFTER slug;
ALTER TABLE agencies ADD COLUMN subscription_state VARCHAR(40) NULL AFTER organization_handle;
UPDATE agencies SET organization_handle = slug WHERE organization_handle IS NULL;
UPDATE agencies SET subscription_state = 'Active' WHERE subscription_state IS NULL;
ALTER TABLE agencies
    MODIFY organization_handle VARCHAR(50) NOT NULL,
    MODIFY subscription_state VARCHAR(40) NOT NULL DEFAULT 'Active';
ALTER TABLE agencies ADD CONSTRAINT uq_agencies_organization_handle UNIQUE (organization_handle);
CREATE INDEX idx_agencies_organization_handle ON agencies(organization_handle);
CREATE INDEX idx_agencies_subscription_state ON agencies(subscription_state);

-- users: role, lead visibility, per-agency email uniqueness
ALTER TABLE users ADD COLUMN role VARCHAR(50) NULL AFTER password_hash;
ALTER TABLE users ADD COLUMN can_view_all_agency_leads BOOLEAN NULL AFTER is_active;
UPDATE users SET role = 'tenant_agent' WHERE role IS NULL;
UPDATE users SET can_view_all_agency_leads = TRUE WHERE can_view_all_agency_leads IS NULL;
ALTER TABLE users
    MODIFY role VARCHAR(50) NOT NULL DEFAULT 'tenant_agent',
    MODIFY can_view_all_agency_leads BOOLEAN NOT NULL DEFAULT TRUE;
CREATE INDEX idx_users_role ON users(role);

-- Promote the first user in the default agency to tenant super user (local dev seed pattern).
UPDATE users u
JOIN (
    SELECT MIN(id) AS id
    FROM users
    WHERE agency_id = '00000000-0000-4000-8000-000000000001'
) first_user ON first_user.id = u.id
SET u.role = 'tenant_super_user'
WHERE u.role = 'tenant_agent';

ALTER TABLE users DROP INDEX email;
ALTER TABLE users ADD CONSTRAINT uq_users_agency_email UNIQUE (agency_id, email);

-- The Bridge: platform-level tenant provisioning invitations
CREATE TABLE IF NOT EXISTS platform_invitations (
    id CHAR(36) PRIMARY KEY,
    target_agency_name VARCHAR(255) NOT NULL,
    target_organization_handle VARCHAR(50) NOT NULL,
    invite_email VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_platform_invitations_org_handle UNIQUE (target_organization_handle),
    CONSTRAINT uq_platform_invitations_token UNIQUE (token)
);
CREATE INDEX idx_platform_invitations_token ON platform_invitations(token);

-- Tenant team invitations
CREATE TABLE IF NOT EXISTS agency_invitations (
    id CHAR(36) PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    invite_email VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'tenant_agent',
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_agency_invitations_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT uq_agency_invitations_token UNIQUE (token)
);
CREATE INDEX idx_agency_invitations_agency ON agency_invitations(agency_id);
CREATE INDEX idx_agency_invitations_token ON agency_invitations(token);

-- Agency-wide agent RBAC config + group ownership for own-vs-other scoping.

ALTER TABLE agency_settings
    ADD COLUMN agent_permissions JSON NULL;

UPDATE agency_settings
SET agent_permissions = JSON_OBJECT()
WHERE agent_permissions IS NULL;

ALTER TABLE agency_groups
    ADD COLUMN created_by_id INT NULL AFTER agency_id;

-- Backfill: prefer oldest tenant_super_user in the agency, else oldest user.
UPDATE agency_groups ag
INNER JOIN (
    SELECT
        u.agency_id,
        u.id AS user_id
    FROM users u
    INNER JOIN (
        SELECT
            agency_id,
            MIN(id) AS min_id
        FROM users
        WHERE agency_id IS NOT NULL
          AND role = 'tenant_super_user'
          AND is_active = TRUE
        GROUP BY agency_id
    ) preferred ON preferred.agency_id = u.agency_id AND preferred.min_id = u.id
) owners ON owners.agency_id = ag.agency_id
SET ag.created_by_id = owners.user_id
WHERE ag.created_by_id IS NULL;

UPDATE agency_groups ag
INNER JOIN (
    SELECT
        u.agency_id,
        u.id AS user_id
    FROM users u
    INNER JOIN (
        SELECT
            agency_id,
            MIN(id) AS min_id
        FROM users
        WHERE agency_id IS NOT NULL
        GROUP BY agency_id
    ) fallback ON fallback.agency_id = u.agency_id AND fallback.min_id = u.id
) owners ON owners.agency_id = ag.agency_id
SET ag.created_by_id = owners.user_id
WHERE ag.created_by_id IS NULL;

-- Any remaining orphans (no users) stay NULL; application treats them as non-owned by agents.
ALTER TABLE agency_groups
    ADD INDEX idx_agency_groups_created_by (created_by_id);

ALTER TABLE agency_groups
    ADD CONSTRAINT fk_agency_groups_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE RESTRICT;

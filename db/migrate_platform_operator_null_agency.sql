-- Platform operators are not bound to a tenant agency.

ALTER TABLE users MODIFY agency_id CHAR(36) NULL;
UPDATE users SET agency_id = NULL WHERE role = 'platform_super_admin';

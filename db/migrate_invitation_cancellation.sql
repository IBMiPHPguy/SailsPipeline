-- Invitation cancellation support (manual revoke + status tracking)
ALTER TABLE platform_invitations ADD COLUMN cancelled_at TIMESTAMP NULL AFTER expires_at;
ALTER TABLE agency_invitations ADD COLUMN cancelled_at TIMESTAMP NULL AFTER expires_at;

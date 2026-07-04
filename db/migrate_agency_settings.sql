-- Phase 3c: Agency white-label settings (branding, contact, legal vault)
-- DDL only for fresh installs (see db/init.sql). Sections below marked UPGRADE ONLY mutate data.

CREATE TABLE IF NOT EXISTS agency_settings (
    agency_id CHAR(36) NOT NULL PRIMARY KEY,
    agency_name VARCHAR(255) NOT NULL,
    brand_logo_url VARCHAR(1024) NULL,
    primary_color VARCHAR(7) NOT NULL DEFAULT '#0d5c75',
    secondary_color VARCHAR(7) NOT NULL DEFAULT '#17a2b8',
    custom_master_tc TEXT NULL,
    email_signature_block TEXT NULL,
    business_address VARCHAR(512) NULL,
    business_phone VARCHAR(50) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_settings_agency FOREIGN KEY (agency_id) REFERENCES agencies (id) ON DELETE CASCADE
);

-- UPGRADE ONLY: backfill settings rows for existing agencies (skip on blank production databases).
INSERT INTO agency_settings (agency_id, agency_name, primary_color, secondary_color, business_address)
SELECT
    a.id,
    a.name,
    '#0d5c75',
    '#17a2b8',
    NULLIF(
        TRIM(
            CONCAT_WS(
                ', ',
                NULLIF(TRIM(a.business_address_line_1), ''),
                NULLIF(TRIM(a.business_address_line_2), ''),
                NULLIF(TRIM(a.business_city), ''),
                NULLIF(TRIM(a.business_state_or_province), ''),
                NULLIF(TRIM(a.business_postal_code), ''),
                NULLIF(TRIM(a.business_country), '')
            )
        ),
        ''
    )
FROM agencies a
ON DUPLICATE KEY UPDATE
    agency_name = VALUES(agency_name),
    business_address = COALESCE(agency_settings.business_address, VALUES(business_address));

-- Seed default tenant branding (agency UUID ...0001).
UPDATE agency_settings
SET
    agency_name = 'Cruise Seakers Travel LLC',
    primary_color = '#0d5c75',
    secondary_color = '#17a2b8'
WHERE agency_id = '00000000-0000-4000-8000-000000000001';

UPDATE agencies
SET name = 'Cruise Seakers Travel LLC'
WHERE id = '00000000-0000-4000-8000-000000000001'
  AND name = 'Default Agency';

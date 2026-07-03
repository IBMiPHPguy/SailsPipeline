-- Expand agency signature/legal fields for large HTML signatures with hosted images.
-- Run: Get-Content db\migrate_agency_signature_mediumtext.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow

ALTER TABLE agency_settings
    MODIFY email_signature_block MEDIUMTEXT NULL,
    MODIFY custom_master_tc MEDIUMTEXT NULL;

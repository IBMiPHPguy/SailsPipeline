-- Add encrypted transient card vault column for burn-after-reading workflow
-- Run: Get-Content db\migrate_cc_auth_encrypted_card_data.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow

ALTER TABLE credit_card_authorizations
    ADD COLUMN encrypted_card_data TEXT NULL AFTER completed_at;

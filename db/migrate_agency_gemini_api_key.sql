-- Tenant-scoped Gemini API key (encrypted at rest) for production AI features.

ALTER TABLE agency_settings
    ADD COLUMN encrypted_gemini_api_key TEXT NULL AFTER business_phone;

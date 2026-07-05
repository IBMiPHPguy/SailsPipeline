ALTER TABLE travel_requests
    ADD COLUMN intake_mode VARCHAR(100) NULL AFTER marketing_campaign_id,
    ADD COLUMN intake_social_platform VARCHAR(50) NULL AFTER intake_mode;

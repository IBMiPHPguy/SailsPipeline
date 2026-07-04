-- Trial period tracking for self-service tenant registrations.
ALTER TABLE agencies
    ADD COLUMN trial_ends_at TIMESTAMP NULL AFTER subscription_state;

CREATE INDEX idx_agencies_trial_ends_at ON agencies (trial_ends_at);

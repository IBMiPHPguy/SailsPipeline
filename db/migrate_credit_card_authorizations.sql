-- Epic 2: Transient Credit Card Authorization Engine
-- Run: Get-Content db\migrate_credit_card_authorizations.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline

CREATE TABLE IF NOT EXISTS credit_card_authorizations (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    secure_token VARCHAR(128) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    expires_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cc_auth_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_cc_auth_travel_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT uq_cc_auth_secure_token UNIQUE (secure_token),
    INDEX idx_cc_auth_travel_request (travel_request_id),
    INDEX idx_cc_auth_agency (agency_id),
    INDEX idx_cc_auth_status_expires (status, expires_at)
);

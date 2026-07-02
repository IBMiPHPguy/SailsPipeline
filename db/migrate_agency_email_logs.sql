-- Epic 1: Immutable audit trail for outbound transactional email delivery.

CREATE TABLE IF NOT EXISTS agency_email_logs (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    user_id INT NOT NULL,
    travel_request_id INT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    email_type VARCHAR(80) NOT NULL,
    subject_line VARCHAR(255) NOT NULL,
    status VARCHAR(40) NOT NULL,
    error_message TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_email_logs_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_agency_email_logs_user
        FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_agency_email_logs_travel_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE SET NULL,
    INDEX idx_agency_email_logs_agency (agency_id),
    INDEX idx_agency_email_logs_user (user_id),
    INDEX idx_agency_email_logs_travel_request (travel_request_id),
    INDEX idx_agency_email_logs_agency_created (agency_id, created_at)
);

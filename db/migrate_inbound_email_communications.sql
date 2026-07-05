ALTER TABLE request_communications
    ADD COLUMN sender_email VARCHAR(255) NULL AFTER body,
    ADD COLUMN received_at DATETIME NULL AFTER sent_at,
    ADD COLUMN is_response_to_agent TINYINT(1) NOT NULL DEFAULT 0 AFTER received_at;

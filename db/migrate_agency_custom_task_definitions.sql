-- Phase 5: agency-owned checklist task definitions for the custom task builder.

CREATE TABLE IF NOT EXISTS agency_custom_task_definitions (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    task_key VARCHAR(80) NOT NULL,
    task_title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    action_type VARCHAR(100) NOT NULL DEFAULT 'manual_check',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_custom_task_definitions_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT uq_agency_custom_task_definitions_key UNIQUE (agency_id, task_key),
    INDEX idx_agency_custom_task_definitions_agency (agency_id)
);

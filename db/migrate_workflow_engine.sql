-- Dynamic multi-tenant workflow template library and live execution instances.

CREATE TABLE IF NOT EXISTS agency_workflow_templates (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    workflow_type_key VARCHAR(40) NULL,
    successor_template_id CHAR(36) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_workflow_templates_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_agency_workflow_templates_successor
        FOREIGN KEY (successor_template_id) REFERENCES agency_workflow_templates(id) ON DELETE SET NULL,
    INDEX idx_agency_workflow_templates_agency (agency_id),
    INDEX idx_agency_workflow_templates_agency_type (agency_id, workflow_type_key)
);

CREATE TABLE IF NOT EXISTS agency_task_templates (
    id CHAR(36) NOT NULL PRIMARY KEY,
    workflow_template_id CHAR(36) NOT NULL,
    task_title VARCHAR(255) NOT NULL,
    sequence_order INT NOT NULL,
    action_type VARCHAR(100) NOT NULL DEFAULT 'manual_check',
    target_field VARCHAR(255) NULL,
    task_key VARCHAR(80) NULL,
    description TEXT NULL,
    prerequisite_task_keys JSON NULL,
    CONSTRAINT fk_agency_task_templates_workflow
        FOREIGN KEY (workflow_template_id) REFERENCES agency_workflow_templates(id) ON DELETE CASCADE,
    INDEX idx_agency_task_templates_workflow (workflow_template_id),
    INDEX idx_agency_task_templates_workflow_order (workflow_template_id, sequence_order)
);

CREATE TABLE IF NOT EXISTS request_workflows_live (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    template_id CHAR(36) NULL,
    workflow_name VARCHAR(255) NOT NULL,
    workflow_type_key VARCHAR(40) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Active',
    parent_workflow_live_id CHAR(36) NULL,
    context JSON NULL,
    started_by_id INT NOT NULL,
    completed_by_id INT NULL,
    legacy_workflow_id INT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    CONSTRAINT fk_request_workflows_live_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_workflows_live_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_workflows_live_template
        FOREIGN KEY (template_id) REFERENCES agency_workflow_templates(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_workflows_live_parent
        FOREIGN KEY (parent_workflow_live_id) REFERENCES request_workflows_live(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_workflows_live_started_by
        FOREIGN KEY (started_by_id) REFERENCES users(id),
    CONSTRAINT fk_request_workflows_live_completed_by
        FOREIGN KEY (completed_by_id) REFERENCES users(id),
    INDEX idx_request_workflows_live_request (travel_request_id),
    INDEX idx_request_workflows_live_agency (agency_id),
    INDEX idx_request_workflows_live_legacy (legacy_workflow_id)
);

-- MySQL partial unique: at most one Active workflow per travel request.
ALTER TABLE request_workflows_live
    ADD COLUMN active_request_key INT GENERATED ALWAYS AS (
        IF(status = 'Active', travel_request_id, NULL)
    ) STORED;

CREATE UNIQUE INDEX uq_request_workflows_live_one_active
    ON request_workflows_live (active_request_key);

CREATE TABLE IF NOT EXISTS request_tasks_live (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    request_workflow_live_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    template_task_id CHAR(36) NULL,
    task_key VARCHAR(80) NULL,
    task_title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    sequence_order INT NOT NULL,
    action_type VARCHAR(100) NOT NULL DEFAULT 'manual_check',
    target_field VARCHAR(255) NULL,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(40) NOT NULL DEFAULT 'Open',
    due_at TIMESTAMP NULL,
    result JSON NULL,
    completed_by_id INT NULL,
    completed_at TIMESTAMP NULL,
    legacy_task_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_tasks_live_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tasks_live_workflow
        FOREIGN KEY (request_workflow_live_id) REFERENCES request_workflows_live(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tasks_live_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tasks_live_template_task
        FOREIGN KEY (template_task_id) REFERENCES agency_task_templates(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_tasks_live_completed_by
        FOREIGN KEY (completed_by_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_request_tasks_live_workflow (request_workflow_live_id),
    INDEX idx_request_tasks_live_request (travel_request_id),
    INDEX idx_request_tasks_live_legacy (legacy_task_id)
);

ALTER TABLE request_communications
    ADD COLUMN request_workflow_live_id CHAR(36) NULL AFTER request_workflow_id;

ALTER TABLE request_communications
    ADD CONSTRAINT fk_request_communications_workflow_live
        FOREIGN KEY (request_workflow_live_id) REFERENCES request_workflows_live(id) ON DELETE SET NULL;

CREATE INDEX idx_request_communications_workflow_live
    ON request_communications(request_workflow_live_id);

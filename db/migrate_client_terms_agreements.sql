-- Master Terms & Conditions: global client agreements and transient portal tokens.

CREATE TABLE IF NOT EXISTS client_terms_agreements (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    client_id INT NOT NULL,
    travel_request_id INT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'accepted',
    accepted_at DATETIME NOT NULL,
    ip_address VARCHAR(64) NULL,
    version_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_client_terms_agreements_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_client_terms_agreements_client
        FOREIGN KEY (client_id) REFERENCES passengers(id) ON DELETE CASCADE,
    CONSTRAINT fk_client_terms_agreements_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE SET NULL,
    UNIQUE KEY uq_client_terms_agreements_agency_client (agency_id, client_id),
    INDEX idx_client_terms_agreements_agency_status (agency_id, status),
    INDEX idx_client_terms_agreements_client (client_id)
);

CREATE TABLE IF NOT EXISTS client_terms_requests (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    client_id INT NOT NULL,
    travel_request_id INT NOT NULL,
    secure_token VARCHAR(128) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    expires_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_client_terms_requests_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_client_terms_requests_client
        FOREIGN KEY (client_id) REFERENCES passengers(id) ON DELETE CASCADE,
    CONSTRAINT fk_client_terms_requests_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    UNIQUE KEY uq_client_terms_requests_token (secure_token),
    INDEX idx_client_terms_requests_status_expires (status, expires_at),
    INDEX idx_client_terms_requests_request (travel_request_id)
);

-- Insert Master T&C task as first step in Enter Trip in CRM (legacy workflows).
UPDATE request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
SET rt.sort_order = rt.sort_order + 1
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.sort_order >= 1;

INSERT INTO request_tasks (
    agency_id,
    request_workflow_id,
    travel_request_id,
    task_key,
    title,
    description,
    status,
    sort_order
)
SELECT
    rw.agency_id,
    rw.id,
    rw.travel_request_id,
    'accept_master_terms_and_conditions',
    'Master Terms & Conditions',
    'Verify or collect the client''s signed Master Terms & Conditions before continuing.',
    'Open',
    1
FROM request_workflows rw
WHERE rw.workflow_type = 'enter_trip_crm'
  AND NOT EXISTS (
      SELECT 1
      FROM request_tasks existing
      WHERE existing.request_workflow_id = rw.id
        AND existing.task_key = 'accept_master_terms_and_conditions'
  );

-- Live workflow engine instances.
UPDATE request_tasks_live rtl
JOIN request_workflows_live rwl ON rwl.id = rtl.request_workflow_live_id
SET rtl.sequence_order = rtl.sequence_order + 1
WHERE rwl.workflow_type_key = 'enter_trip_crm'
  AND rtl.sequence_order >= 1;

INSERT INTO request_tasks_live (
    id,
    agency_id,
    request_workflow_live_id,
    travel_request_id,
    task_key,
    task_title,
    description,
    sequence_order,
    action_type,
    status,
    is_completed
)
SELECT
    UUID(),
    rwl.agency_id,
    rwl.id,
    rwl.travel_request_id,
    'accept_master_terms_and_conditions',
    'Master Terms & Conditions',
    'Verify or collect the client''s signed Master Terms & Conditions before continuing.',
    1,
    'custom_panel',
    'Open',
    FALSE
FROM request_workflows_live rwl
WHERE rwl.workflow_type_key = 'enter_trip_crm'
  AND NOT EXISTS (
      SELECT 1
      FROM request_tasks_live existing
      WHERE existing.request_workflow_live_id = rwl.id
        AND existing.task_key = 'accept_master_terms_and_conditions'
  );

-- Agency workflow templates (seeded playbooks).
UPDATE agency_task_templates att
JOIN agency_workflow_templates awt ON awt.id = att.workflow_template_id
SET att.sequence_order = att.sequence_order + 1
WHERE awt.workflow_type = 'enter_trip_crm'
  AND att.sequence_order >= 1;

INSERT INTO agency_task_templates (
    id,
    workflow_template_id,
    task_title,
    sequence_order,
    action_type,
    task_key,
    description
)
SELECT
    UUID(),
    awt.id,
    'Master Terms & Conditions',
    1,
    'custom_panel',
    'accept_master_terms_and_conditions',
    'Verify or collect the client''s signed Master Terms & Conditions before continuing.'
FROM agency_workflow_templates awt
WHERE awt.workflow_type_key = 'enter_trip_crm'
  AND awt.archived_at IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM agency_task_templates existing
      WHERE existing.workflow_template_id = awt.id
        AND existing.task_key = 'accept_master_terms_and_conditions'
  );

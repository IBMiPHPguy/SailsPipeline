-- Epic 4: Travel Insurance Validation and Waiver Pipeline

ALTER TABLE passengers
    ADD COLUMN has_annual_insurance BOOLEAN NOT NULL DEFAULT FALSE AFTER is_active,
    ADD COLUMN annual_insurance_expires_at DATE NULL AFTER has_annual_insurance,
    ADD COLUMN annual_insurance_policy_number VARCHAR(80) NULL AFTER annual_insurance_expires_at;

ALTER TABLE quoted_insurance
    ADD COLUMN quote_mailed BOOLEAN NOT NULL DEFAULT FALSE AFTER declined_at;

CREATE TABLE IF NOT EXISTS request_insurance_tracking (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    insurance_status VARCHAR(40) NOT NULL DEFAULT 'pending',
    waiver_signed_at DATETIME NULL,
    waiver_ip VARCHAR(64) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_insurance_tracking_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_insurance_tracking_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    UNIQUE KEY uq_request_insurance_tracking_request (travel_request_id),
    INDEX idx_request_insurance_tracking_status (insurance_status)
);

CREATE TABLE IF NOT EXISTS insurance_waiver_requests (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    secure_token VARCHAR(128) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'pending',
    expires_at DATETIME NOT NULL,
    completed_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_insurance_waiver_requests_agency
        FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    CONSTRAINT fk_insurance_waiver_requests_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    UNIQUE KEY uq_insurance_waiver_requests_token (secure_token),
    INDEX idx_insurance_waiver_requests_status_expires (status, expires_at),
    INDEX idx_insurance_waiver_requests_request (travel_request_id)
);

-- Insert Travel Insurance task before Collect deposit / final payment (sort_order 5).
UPDATE request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
SET rt.sort_order = rt.sort_order + 1
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.sort_order >= 5;

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
    'verify_travel_insurance',
    'Travel insurance validation',
    'Confirm annual insurance coverage or verify per-trip insurance quotes and waiver compliance.',
    'Open',
    5
FROM request_workflows rw
WHERE rw.workflow_type = 'enter_trip_crm'
  AND NOT EXISTS (
      SELECT 1
      FROM request_tasks existing
      WHERE existing.request_workflow_id = rw.id
        AND existing.task_key = 'verify_travel_insurance'
  );

UPDATE request_tasks_live rtl
JOIN request_workflows_live rwl ON rwl.id = rtl.request_workflow_live_id
SET rtl.sequence_order = rtl.sequence_order + 1
WHERE rwl.workflow_type_key = 'enter_trip_crm'
  AND rtl.sequence_order >= 5;

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
    'verify_travel_insurance',
    'Travel insurance validation',
    'Confirm annual insurance coverage or verify per-trip insurance quotes and waiver compliance.',
    5,
    'custom_panel',
    'Open',
    FALSE
FROM request_workflows_live rwl
WHERE rwl.workflow_type_key = 'enter_trip_crm'
  AND NOT EXISTS (
      SELECT 1
      FROM request_tasks_live existing
      WHERE existing.request_workflow_live_id = rwl.id
        AND existing.task_key = 'verify_travel_insurance'
  );

UPDATE agency_task_templates att
JOIN agency_workflow_templates awt ON awt.id = att.workflow_template_id
SET att.sequence_order = att.sequence_order + 1
WHERE awt.workflow_type_key = 'enter_trip_crm'
  AND att.sequence_order >= 5;

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
    'Travel insurance validation',
    5,
    'custom_panel',
    'verify_travel_insurance',
    'Confirm annual insurance coverage or verify per-trip insurance quotes and waiver compliance.'
FROM agency_workflow_templates awt
WHERE awt.workflow_type_key = 'enter_trip_crm'
  AND awt.archived_at IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM agency_task_templates existing
      WHERE existing.workflow_template_id = awt.id
        AND existing.task_key = 'verify_travel_insurance'
  );

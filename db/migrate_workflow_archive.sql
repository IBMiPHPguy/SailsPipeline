-- Soft-delete agency workflows while preserving rows for audit history links.

ALTER TABLE agency_workflow_templates
    ADD COLUMN archived_at TIMESTAMP NULL DEFAULT NULL AFTER created_at;

CREATE INDEX idx_agency_workflow_templates_agency_archived
    ON agency_workflow_templates (agency_id, archived_at);

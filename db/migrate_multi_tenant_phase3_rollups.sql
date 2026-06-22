-- Phase 3a: agency dashboard rollups and report metadata caches

CREATE TABLE IF NOT EXISTS agency_dashboard_rollups (
    agency_id CHAR(36) NOT NULL PRIMARY KEY,
    open_leads_count INT NOT NULL DEFAULT 0,
    proposals_pending_count INT NOT NULL DEFAULT 0,
    completed_bookings_count INT NOT NULL DEFAULT 0,
    total_volume_booked DECIMAL(15, 2) NOT NULL DEFAULT 0,
    total_commission_booked DECIMAL(15, 2) NOT NULL DEFAULT 0,
    stale_count INT NOT NULL DEFAULT 0,
    closed_count INT NOT NULL DEFAULT 0,
    purchased_closed_count INT NOT NULL DEFAULT 0,
    total_pipeline_value DECIMAL(15, 2) NOT NULL DEFAULT 0,
    last_refreshed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_dashboard_rollups_agency FOREIGN KEY (agency_id) REFERENCES agencies(id)
);

CREATE TABLE IF NOT EXISTS agency_report_metadata_caches (
    agency_id CHAR(36) NOT NULL PRIMARY KEY,
    active_advisor_names JSON NOT NULL,
    active_residence_states JSON NOT NULL,
    last_refreshed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_report_metadata_caches_agency FOREIGN KEY (agency_id) REFERENCES agencies(id)
);

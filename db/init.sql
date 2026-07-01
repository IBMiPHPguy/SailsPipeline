CREATE TABLE IF NOT EXISTS agencies (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(80) NOT NULL UNIQUE,
    organization_handle VARCHAR(50) NOT NULL,
    subscription_state VARCHAR(40) NOT NULL DEFAULT 'Active',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_agencies_organization_handle UNIQUE (organization_handle)
);

CREATE INDEX idx_agencies_organization_handle ON agencies(organization_handle);
CREATE INDEX idx_agencies_subscription_state ON agencies(subscription_state);

INSERT INTO agencies (id, name, slug, organization_handle, subscription_state)
VALUES ('00000000-0000-4000-8000-000000000001', 'Default Agency', 'default', 'default', 'Active');

CREATE TABLE IF NOT EXISTS platform_invitations (
    id CHAR(36) PRIMARY KEY,
    target_agency_name VARCHAR(255) NOT NULL,
    target_organization_handle VARCHAR(50) NOT NULL,
    invite_email VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    cancelled_at TIMESTAMP NULL,
    CONSTRAINT uq_platform_invitations_org_handle UNIQUE (target_organization_handle),
    CONSTRAINT uq_platform_invitations_token UNIQUE (token)
);

CREATE INDEX idx_platform_invitations_token ON platform_invitations(token);

CREATE TABLE IF NOT EXISTS agency_invitations (
    id CHAR(36) PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    invite_email VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'tenant_agent',
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    cancelled_at TIMESTAMP NULL,
    CONSTRAINT fk_agency_invitations_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT uq_agency_invitations_token UNIQUE (token)
);

CREATE INDEX idx_agency_invitations_agency ON agency_invitations(agency_id);
CREATE INDEX idx_agency_invitations_token ON agency_invitations(token);

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
    marketing_active_monthly_budget DECIMAL(15, 2) NOT NULL DEFAULT 0,
    marketing_top_roi_campaign_name VARCHAR(255) NULL,
    marketing_top_roi_percent DECIMAL(10, 2) NULL,
    marketing_total_attributed_volume DECIMAL(15, 2) NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NULL,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'tenant_agent',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    can_view_all_agency_leads BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT uq_users_agency_email UNIQUE (agency_id, email)
);

CREATE INDEX idx_users_agency ON users(agency_id);
CREATE INDEX idx_users_role ON users(role);

CREATE TABLE IF NOT EXISTS travel_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    cruise_lines JSON NOT NULL,
    excluded_cruise_lines JSON NOT NULL,
    destination VARCHAR(120) NOT NULL,
    destination_details JSON NULL,
    ship_name VARCHAR(100) NULL,
    departure_date DATE NOT NULL,
    return_date DATE NOT NULL,
    cabin_types JSON NOT NULL,
    qualifiers JSON NOT NULL,
    passengers INT NOT NULL DEFAULT 1,
    cabins_needed INT NOT NULL DEFAULT 1,
    cabin_hold_reservation_ids JSON NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Open',
    close_reason VARCHAR(120) NULL,
    lead_source VARCHAR(100) NULL,
    referral_source_name VARCHAR(255) NULL,
    marketing_campaign_id CHAR(36) NULL,
    group_id CHAR(36) NULL,
    group_inventory_id CHAR(36) NULL,
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_travel_requests_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_travel_requests_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_travel_requests_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS marketing_campaigns (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    campaign_type VARCHAR(100) NOT NULL,
    monthly_spend DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_marketing_campaigns_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    INDEX idx_marketing_campaigns_agency (agency_id),
    INDEX idx_marketing_campaigns_agency_start (agency_id, start_date)
);

ALTER TABLE travel_requests
    ADD CONSTRAINT fk_travel_requests_marketing_campaign
        FOREIGN KEY (marketing_campaign_id) REFERENCES marketing_campaigns(id) ON DELETE SET NULL;

CREATE INDEX idx_travel_requests_marketing_campaign ON travel_requests(marketing_campaign_id);

CREATE TABLE IF NOT EXISTS agency_groups (
    id CHAR(36) NOT NULL PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    group_name VARCHAR(255) NOT NULL,
    cruise_line VARCHAR(100) NOT NULL,
    ship_name VARCHAR(100) NOT NULL,
    sailing_date DATE NOT NULL,
    disembarkation_date DATE NOT NULL,
    group_id_code VARCHAR(100) NULL,
    group_amenities TEXT NULL,
    tc_ratio VARCHAR(50) NULL DEFAULT '1:16',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_groups_agency FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE,
    INDEX idx_agency_groups_agency (agency_id),
    INDEX idx_agency_groups_agency_active (agency_id, is_active),
    INDEX idx_agency_groups_agency_sailing (agency_id, sailing_date)
);

CREATE TABLE IF NOT EXISTS agency_group_inventory (
    id CHAR(36) NOT NULL PRIMARY KEY,
    group_id CHAR(36) NOT NULL,
    cabin_category VARCHAR(50) NOT NULL,
    cabin_type VARCHAR(100) NOT NULL,
    cabin_description TEXT NULL,
    price_per_cabin DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    deposit_per_cabin DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    cabins_allocated INT NOT NULL DEFAULT 0,
    cabins_reserved INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_group_inventory_group FOREIGN KEY (group_id) REFERENCES agency_groups(id) ON DELETE CASCADE,
    CONSTRAINT uq_agency_group_inventory_category UNIQUE (group_id, cabin_category),
    INDEX idx_agency_group_inventory_group (group_id)
);

ALTER TABLE travel_requests
    ADD CONSTRAINT fk_travel_requests_group
        FOREIGN KEY (group_id) REFERENCES agency_groups(id) ON DELETE SET NULL;

ALTER TABLE travel_requests
    ADD CONSTRAINT fk_travel_requests_group_inventory
        FOREIGN KEY (group_inventory_id) REFERENCES agency_group_inventory(id) ON DELETE SET NULL;

CREATE INDEX idx_travel_requests_group ON travel_requests(group_id);

CREATE TABLE IF NOT EXISTS travel_request_group_bookings (
    id CHAR(36) NOT NULL PRIMARY KEY,
    travel_request_id INT NOT NULL,
    group_inventory_id CHAR(36) NOT NULL,
    cabins_requested INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_travel_request_group_bookings_request
        FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_travel_request_group_bookings_inventory
        FOREIGN KEY (group_inventory_id) REFERENCES agency_group_inventory(id) ON DELETE CASCADE,
    CONSTRAINT uq_travel_request_group_booking UNIQUE (travel_request_id, group_inventory_id),
    INDEX idx_travel_request_group_bookings_request (travel_request_id),
    INDEX idx_travel_request_group_bookings_inventory (group_inventory_id)
);

CREATE TABLE IF NOT EXISTS call_transcripts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes INT NOT NULL,
    created_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_call_transcripts_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_call_transcripts_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_call_transcripts_user FOREIGN KEY (created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS chat_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes INT NOT NULL,
    created_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_logs_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_chat_logs_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_logs_user FOREIGN KEY (created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS passengers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(255) NULL,
    phone VARCHAR(30) NULL,
    date_of_birth DATE NULL,
    address_line_1 VARCHAR(120) NULL,
    address_line_2 VARCHAR(120) NULL,
    city VARCHAR(80) NULL,
    state_or_province VARCHAR(50) NULL,
    postal_code VARCHAR(20) NULL,
    country VARCHAR(80) NULL,
    qualifiers JSON NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_passengers_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_passengers_created_by FOREIGN KEY (created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_passengers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    travel_request_id INT NOT NULL,
    passenger_id INT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    qualifiers JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_request_passengers_travel_request (travel_request_id),
    INDEX idx_request_passengers_passenger (passenger_id),
    CONSTRAINT fk_request_passengers_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_passengers_passenger FOREIGN KEY (passenger_id) REFERENCES passengers(id),
    CONSTRAINT uq_request_passengers_request_passenger UNIQUE (travel_request_id, passenger_id)
);

CREATE TABLE IF NOT EXISTS request_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    summary VARCHAR(160) NOT NULL,
    content TEXT NOT NULL,
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_notes_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_request_notes_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_notes_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_request_notes_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_note_audits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_note_id INT NOT NULL,
    from_summary VARCHAR(160) NULL,
    to_summary VARCHAR(160) NULL,
    from_content TEXT NULL,
    to_content TEXT NULL,
    changed_by_id INT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_note_audits_note FOREIGN KEY (request_note_id) REFERENCES request_notes(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_note_audits_user FOREIGN KEY (changed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS travel_request_audits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    travel_request_id INT NOT NULL,
    field_name VARCHAR(80) NOT NULL,
    from_value TEXT NULL,
    to_value TEXT NULL,
    changed_by_id INT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_travel_request_audits_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_travel_request_audits_user FOREIGN KEY (changed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_passenger_audits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    travel_request_id INT NOT NULL,
    request_passenger_id INT NULL,
    passenger_label VARCHAR(161) NULL,
    field_name VARCHAR(80) NOT NULL,
    from_value TEXT NULL,
    to_value TEXT NULL,
    changed_by_id INT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_passenger_audits_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_passenger_audits_user FOREIGN KEY (changed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS proposed_cruises (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    departure_date DATE NOT NULL,
    cruise_line VARCHAR(120) NOT NULL,
    ship VARCHAR(120) NOT NULL,
    number_of_nights INT NOT NULL,
    itinerary_name VARCHAR(160) NOT NULL,
    itinerary_details TEXT NULL,
    room_category VARCHAR(120) NOT NULL,
    room_number VARCHAR(40) NOT NULL,
    passengers_in_room INT NOT NULL,
    deposit_amount DECIMAL(10, 2) NOT NULL,
    deposit_due_date DATE NOT NULL,
    final_payment_due_date DATE NOT NULL,
    cost DECIMAL(10, 2) NOT NULL,
    cabin_pricing JSON NULL,
    cabin_rooms JSON NULL,
    cabin_hold_reservation_ids JSON NULL,
    includes JSON NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Proposed',
    rejection_reason VARCHAR(120) NULL,
    rejection_reason_detail VARCHAR(500) NULL,
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_proposed_cruises_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_proposed_cruises_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_proposed_cruises_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_proposed_cruises_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS proposed_cruise_passengers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proposed_cruise_id INT NOT NULL,
    request_passenger_id INT NOT NULL,
    cabin_index INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_proposed_cruise_passengers_cruise FOREIGN KEY (proposed_cruise_id) REFERENCES proposed_cruises(id) ON DELETE CASCADE,
    CONSTRAINT fk_proposed_cruise_passengers_passenger FOREIGN KEY (request_passenger_id) REFERENCES request_passengers(id) ON DELETE CASCADE,
    CONSTRAINT uq_proposed_cruise_passenger UNIQUE (proposed_cruise_id, request_passenger_id)
);

CREATE TABLE IF NOT EXISTS quoted_insurance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    carrier VARCHAR(120) NOT NULL,
    premium_cost DECIMAL(10, 2) NOT NULL,
    plan_name VARCHAR(160) NOT NULL,
    cancellation_coverage DECIMAL(10, 2) NOT NULL,
    medical_coverage DECIMAL(10, 2) NOT NULL,
    medical_evac_coverage DECIMAL(10, 2) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Proposed',
    declined_at TIMESTAMP NULL,
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_quoted_insurance_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_quoted_insurance_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_quoted_insurance_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_quoted_insurance_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_workflows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    workflow_type VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Active',
    parent_workflow_id INT NULL,
    context JSON NULL,
    started_by_id INT NOT NULL,
    completed_by_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    CONSTRAINT fk_request_workflows_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_request_workflows_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_workflows_parent FOREIGN KEY (parent_workflow_id) REFERENCES request_workflows(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_workflows_started_by FOREIGN KEY (started_by_id) REFERENCES users(id),
    CONSTRAINT fk_request_workflows_completed_by FOREIGN KEY (completed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    request_workflow_id INT NOT NULL,
    travel_request_id INT NOT NULL,
    task_key VARCHAR(80) NOT NULL,
    title VARCHAR(160) NOT NULL,
    description TEXT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Open',
    sort_order INT NOT NULL DEFAULT 0,
    due_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    completed_by_id INT NULL,
    result JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_tasks_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_request_tasks_workflow FOREIGN KEY (request_workflow_id) REFERENCES request_workflows(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tasks_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tasks_completed_by FOREIGN KEY (completed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_communications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    request_workflow_id INT NULL,
    communication_type VARCHAR(40) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Draft',
    sent_at TIMESTAMP NULL,
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_communications_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_request_communications_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_communications_workflow FOREIGN KEY (request_workflow_id) REFERENCES request_workflows(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_communications_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_request_communications_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_research_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agency_id CHAR(36) NOT NULL,
    travel_request_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes INT NOT NULL,
    uploaded_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_research_documents_agency FOREIGN KEY (agency_id) REFERENCES agencies(id),
    CONSTRAINT fk_request_research_documents_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_research_documents_user FOREIGN KEY (uploaded_by_id) REFERENCES users(id)
);

-- Performance indexes (dashboard, reports, analytics)
CREATE INDEX idx_travel_requests_agency ON travel_requests(agency_id);
CREATE INDEX idx_travel_requests_agency_status ON travel_requests(agency_id, status);
CREATE INDEX idx_travel_requests_status ON travel_requests(status);
CREATE INDEX idx_travel_requests_created_at ON travel_requests(created_at);
CREATE INDEX idx_travel_requests_created_by ON travel_requests(created_by_id);
CREATE INDEX idx_travel_requests_status_created ON travel_requests(status, created_at);

CREATE INDEX idx_proposed_cruises_agency ON proposed_cruises(agency_id);
CREATE INDEX idx_proposed_cruises_status ON proposed_cruises(status);
CREATE INDEX idx_proposed_cruises_cruise_line ON proposed_cruises(cruise_line);
CREATE INDEX idx_proposed_cruises_departure ON proposed_cruises(departure_date);
CREATE INDEX idx_proposed_cruises_request_status ON proposed_cruises(travel_request_id, status);

CREATE INDEX idx_passengers_agency ON passengers(agency_id);
CREATE INDEX idx_passengers_agency_active ON passengers(agency_id, is_active);
CREATE INDEX idx_passengers_is_active ON passengers(is_active);
CREATE INDEX idx_passengers_last_first ON passengers(last_name, first_name);
CREATE INDEX idx_passengers_state ON passengers(state_or_province);
CREATE INDEX idx_passengers_email ON passengers(email);
CREATE INDEX idx_passengers_phone ON passengers(phone);

CREATE INDEX idx_tra_request_field ON travel_request_audits(travel_request_id, field_name);
CREATE INDEX idx_tra_changed_at ON travel_request_audits(changed_at);

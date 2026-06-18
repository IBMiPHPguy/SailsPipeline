CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS travel_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(80) NOT NULL,
    last_name VARCHAR(80) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    cruise_lines JSON NOT NULL,
    excluded_cruise_lines JSON NOT NULL,
    destination VARCHAR(120) NOT NULL,
    destination_details JSON NULL,
    departure_date DATE NOT NULL,
    return_date DATE NOT NULL,
    cabin_types JSON NOT NULL,
    qualifiers JSON NOT NULL,
    passengers INT NOT NULL DEFAULT 1,
    cabins_needed INT NOT NULL DEFAULT 1,
    cabin_hold_reservation_ids JSON NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Open',
    close_reason VARCHAR(120) NULL,
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_travel_requests_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_travel_requests_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS call_transcripts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    travel_request_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes INT NOT NULL,
    created_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_call_transcripts_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_call_transcripts_user FOREIGN KEY (created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS chat_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    travel_request_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes INT NOT NULL,
    created_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_logs_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_logs_user FOREIGN KEY (created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS passengers (
    id INT AUTO_INCREMENT PRIMARY KEY,
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
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
    CONSTRAINT fk_request_passengers_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_passengers_passenger FOREIGN KEY (passenger_id) REFERENCES passengers(id),
    CONSTRAINT uq_request_passengers_request_passenger UNIQUE (travel_request_id, passenger_id)
);

CREATE TABLE IF NOT EXISTS request_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    travel_request_id INT NOT NULL,
    summary VARCHAR(160) NOT NULL,
    content TEXT NOT NULL,
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
    includes JSON NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'Proposed',
    created_by_id INT NOT NULL,
    updated_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
    CONSTRAINT fk_quoted_insurance_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_quoted_insurance_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_quoted_insurance_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_workflows (
    id INT AUTO_INCREMENT PRIMARY KEY,
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
    CONSTRAINT fk_request_workflows_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_workflows_parent FOREIGN KEY (parent_workflow_id) REFERENCES request_workflows(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_workflows_started_by FOREIGN KEY (started_by_id) REFERENCES users(id),
    CONSTRAINT fk_request_workflows_completed_by FOREIGN KEY (completed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
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
    CONSTRAINT fk_request_tasks_workflow FOREIGN KEY (request_workflow_id) REFERENCES request_workflows(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tasks_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_tasks_completed_by FOREIGN KEY (completed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_communications (
    id INT AUTO_INCREMENT PRIMARY KEY,
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
    CONSTRAINT fk_request_communications_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_communications_workflow FOREIGN KEY (request_workflow_id) REFERENCES request_workflows(id) ON DELETE SET NULL,
    CONSTRAINT fk_request_communications_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_request_communications_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_research_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    travel_request_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes INT NOT NULL,
    uploaded_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_request_research_documents_request FOREIGN KEY (travel_request_id) REFERENCES travel_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_request_research_documents_user FOREIGN KEY (uploaded_by_id) REFERENCES users(id)
);

-- Agency group shells, child inventory ledger, and travel request linkage.

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
    cabins_allocated INT NOT NULL DEFAULT 0,
    cabins_reserved INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_agency_group_inventory_group FOREIGN KEY (group_id) REFERENCES agency_groups(id) ON DELETE CASCADE,
    CONSTRAINT uq_agency_group_inventory_category UNIQUE (group_id, cabin_category),
    INDEX idx_agency_group_inventory_group (group_id)
);

ALTER TABLE travel_requests
    ADD COLUMN ship_name VARCHAR(100) NULL AFTER destination_details,
    ADD COLUMN group_id CHAR(36) NULL AFTER marketing_campaign_id,
    ADD COLUMN group_inventory_id CHAR(36) NULL AFTER group_id;

ALTER TABLE travel_requests
    ADD CONSTRAINT fk_travel_requests_group
        FOREIGN KEY (group_id) REFERENCES agency_groups(id) ON DELETE SET NULL;

ALTER TABLE travel_requests
    ADD CONSTRAINT fk_travel_requests_group_inventory
        FOREIGN KEY (group_inventory_id) REFERENCES agency_group_inventory(id) ON DELETE SET NULL;

CREATE INDEX idx_travel_requests_group ON travel_requests(group_id);

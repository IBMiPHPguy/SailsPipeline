-- Multi-line group inventory bookings on travel requests (Epic 3).

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

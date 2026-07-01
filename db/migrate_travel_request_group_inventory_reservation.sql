-- Track whether group inventory was reserved when a request closed as purchased.
ALTER TABLE travel_requests
    ADD COLUMN group_inventory_reservation_applied TINYINT(1) NOT NULL DEFAULT 0
        AFTER group_inventory_id;

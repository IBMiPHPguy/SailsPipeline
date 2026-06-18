ALTER TABLE travel_requests
    ADD COLUMN cabin_hold_reservation_ids JSON NULL AFTER cabins_needed;

ALTER TABLE proposed_cruise_passengers
    ADD COLUMN cabin_index INT NOT NULL DEFAULT 0 AFTER request_passenger_id;

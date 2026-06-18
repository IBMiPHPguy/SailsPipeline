ALTER TABLE proposed_cruises
    ADD COLUMN cabin_rooms JSON NULL AFTER cabin_pricing;

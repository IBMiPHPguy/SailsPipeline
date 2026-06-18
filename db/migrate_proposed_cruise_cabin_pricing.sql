ALTER TABLE proposed_cruises
    ADD COLUMN cabin_pricing JSON NULL AFTER cost;

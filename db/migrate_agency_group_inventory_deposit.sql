-- Per-cabin deposit required for group block inventory rows.
ALTER TABLE agency_group_inventory
    ADD COLUMN deposit_per_cabin DECIMAL(10, 2) NOT NULL DEFAULT 0.00 AFTER price_per_cabin;

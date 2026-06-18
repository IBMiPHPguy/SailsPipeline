ALTER TABLE travel_requests
    ADD COLUMN cruise_lines JSON NULL AFTER state_of_residency,
    ADD COLUMN excluded_cruise_lines JSON NOT NULL DEFAULT (JSON_ARRAY()) AFTER cruise_lines;

UPDATE travel_requests
SET cruise_lines = JSON_ARRAY(cruise_line)
WHERE cruise_line IS NOT NULL AND TRIM(cruise_line) <> '';

UPDATE travel_requests
SET excluded_cruise_lines = JSON_ARRAY(excluded_cruise_line)
WHERE excluded_cruise_line IS NOT NULL AND TRIM(excluded_cruise_line) <> '';

UPDATE travel_requests
SET cruise_lines = JSON_ARRAY('Unknown')
WHERE cruise_lines IS NULL;

ALTER TABLE travel_requests
    DROP COLUMN cruise_line,
    DROP COLUMN excluded_cruise_line;

ALTER TABLE travel_requests
    MODIFY cruise_lines JSON NOT NULL;

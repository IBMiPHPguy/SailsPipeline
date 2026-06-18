UPDATE travel_requests
SET cruise_lines = '["Celebrity Cruises"]'
WHERE JSON_CONTAINS(cruise_lines, '"Celebrity"');

UPDATE travel_requests
SET excluded_cruise_lines = '["Carnival Cruise Lines"]'
WHERE JSON_CONTAINS(excluded_cruise_lines, '"Carnival"');

UPDATE travel_requests
SET cruise_lines = '["Royal Caribbean International"]'
WHERE JSON_CONTAINS(cruise_lines, '"Unknown"');

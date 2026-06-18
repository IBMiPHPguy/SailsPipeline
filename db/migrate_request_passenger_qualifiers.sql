ALTER TABLE request_passengers
    ADD COLUMN qualifiers JSON NOT NULL DEFAULT (JSON_ARRAY()) AFTER is_primary;

UPDATE request_passengers rp
INNER JOIN travel_requests tr ON tr.id = rp.travel_request_id
SET rp.qualifiers = tr.qualifiers
WHERE rp.is_primary = TRUE
  AND JSON_LENGTH(COALESCE(tr.qualifiers, JSON_ARRAY())) > 0;

UPDATE request_passengers rp
INNER JOIN (
    SELECT travel_request_id, MIN(id) AS first_passenger_id
    FROM request_passengers
    GROUP BY travel_request_id
) first_passenger ON first_passenger.first_passenger_id = rp.id
INNER JOIN travel_requests tr ON tr.id = rp.travel_request_id
SET rp.qualifiers = tr.qualifiers
WHERE JSON_LENGTH(COALESCE(tr.qualifiers, JSON_ARRAY())) > 0
  AND JSON_LENGTH(COALESCE(rp.qualifiers, JSON_ARRAY())) = 0;

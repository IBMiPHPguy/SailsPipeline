ALTER TABLE proposed_cruises
    ADD COLUMN cabin_hold_reservation_ids JSON NULL AFTER cabin_rooms;

-- Copy request-level reservation IDs only when the request has a single accepted/deposited cruise.
UPDATE proposed_cruises pc
JOIN travel_requests tr ON tr.id = pc.travel_request_id
JOIN (
    SELECT travel_request_id
    FROM proposed_cruises
    WHERE status IN ('Accepted', 'Deposited')
    GROUP BY travel_request_id
    HAVING COUNT(*) = 1
) single_request ON single_request.travel_request_id = pc.travel_request_id
SET pc.cabin_hold_reservation_ids = tr.cabin_hold_reservation_ids
WHERE pc.status IN ('Accepted', 'Deposited')
  AND tr.cabin_hold_reservation_ids IS NOT NULL
  AND JSON_LENGTH(tr.cabin_hold_reservation_ids) > 0;

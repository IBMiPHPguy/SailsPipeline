DELETE rt
FROM request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.task_key IN ('collect_deposit_or_final_payment', 'send_cruise_line_booking_communication');

UPDATE request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
SET rt.sort_order = CASE rt.task_key
    WHEN 'create_trip_in_crm' THEN 5
    WHEN 'send_agency_crm_communication' THEN 6
    WHEN 'setup_crm_final_payment_followups' THEN 7
    WHEN 'record_promised_obc' THEN 8
    ELSE rt.sort_order
END
WHERE rw.workflow_type = 'enter_trip_crm';

INSERT INTO request_tasks (
    request_workflow_id,
    travel_request_id,
    task_key,
    title,
    description,
    status,
    sort_order
)
SELECT
    rw.id,
    rw.travel_request_id,
    'collect_payment_and_send_booking_communication',
    'Collect deposit or final payment and send cruise line communications',
    'Collect payment for each cabin hold, send booking communications, then mark this task done.',
    'Open',
    4
FROM request_workflows rw
WHERE rw.workflow_type = 'enter_trip_crm'
  AND NOT EXISTS (
      SELECT 1
      FROM request_tasks existing
      WHERE existing.request_workflow_id = rw.id
        AND existing.task_key = 'collect_payment_and_send_booking_communication'
  );

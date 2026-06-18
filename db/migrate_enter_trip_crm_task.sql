-- Merge create_trip_in_crm, send_agency_crm_communication, and setup_crm_final_payment_followups
-- into a single Enter Trip in CRM task. Remove record_promised_obc (OBC is on room details).

UPDATE request_tasks target
JOIN request_workflows rw ON rw.id = target.request_workflow_id
LEFT JOIN request_tasks agency
    ON agency.request_workflow_id = rw.id
   AND agency.task_key = 'send_agency_crm_communication'
LEFT JOIN request_tasks followups
    ON followups.request_workflow_id = rw.id
   AND followups.task_key = 'setup_crm_final_payment_followups'
LEFT JOIN (
    SELECT
        request_workflow_id,
        MAX(completed_at) AS last_completed_at,
        SUBSTRING_INDEX(
            GROUP_CONCAT(completed_by_id ORDER BY completed_at DESC),
            ',',
            1
        ) AS last_completed_by_id
    FROM request_tasks
    WHERE task_key IN (
        'create_trip_in_crm',
        'send_agency_crm_communication',
        'setup_crm_final_payment_followups'
    )
      AND status = 'Done'
    GROUP BY request_workflow_id
) merged_done ON merged_done.request_workflow_id = rw.id
SET
    target.title = 'Enter Trip in CRM',
    target.description = 'Create the trip and bookings in your agency CRM, send the agency invoice, then check off each step below.',
    target.sort_order = 5,
    target.result = JSON_OBJECT(
        'create_trip',
        IF(target.status = 'Done', TRUE, FALSE),
        'create_bookings',
        IF(followups.status = 'Done', TRUE, FALSE),
        'sent_agency_invoice',
        IF(agency.status = 'Done', TRUE, FALSE)
    ),
    target.status = CASE
        WHEN target.status = 'Done'
         AND agency.status = 'Done'
         AND followups.status = 'Done'
        THEN 'Done'
        ELSE 'Open'
    END,
    target.completed_at = CASE
        WHEN target.status = 'Done'
         AND agency.status = 'Done'
         AND followups.status = 'Done'
        THEN merged_done.last_completed_at
        ELSE NULL
    END,
    target.completed_by_id = CASE
        WHEN target.status = 'Done'
         AND agency.status = 'Done'
         AND followups.status = 'Done'
        THEN merged_done.last_completed_by_id
        ELSE NULL
    END
WHERE rw.workflow_type = 'enter_trip_crm'
  AND target.task_key = 'create_trip_in_crm';

DELETE rt
FROM request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.task_key IN (
      'send_agency_crm_communication',
      'setup_crm_final_payment_followups',
      'record_promised_obc'
  );

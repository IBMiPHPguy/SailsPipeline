-- Merge verify_dates_of_birth, verify_names_spellings, and verify_email_phone
-- into a single verify_passenger_details task for Enter Trip in CRM workflows.

UPDATE request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
LEFT JOIN (
    SELECT
        request_workflow_id,
        MIN(CASE WHEN status = 'Done' THEN 1 ELSE 0 END) AS all_done,
        MAX(completed_at) AS last_completed_at
    FROM request_tasks
    WHERE task_key IN ('verify_dates_of_birth', 'verify_names_spellings', 'verify_email_phone')
    GROUP BY request_workflow_id
) verify_agg ON verify_agg.request_workflow_id = rt.request_workflow_id
LEFT JOIN request_tasks email_task
    ON email_task.request_workflow_id = rt.request_workflow_id
   AND email_task.task_key = 'verify_email_phone'
SET
    rt.task_key = 'verify_passenger_details',
    rt.title = 'Verify passenger details',
    rt.description = 'Verify names, dates of birth, and contact information for each passenger.',
    rt.sort_order = 1,
    rt.status = CASE WHEN verify_agg.all_done = 1 THEN 'Done' ELSE 'Open' END,
    rt.completed_at = CASE WHEN verify_agg.all_done = 1 THEN verify_agg.last_completed_at ELSE NULL END,
    rt.completed_by_id = CASE WHEN verify_agg.all_done = 1 THEN email_task.completed_by_id ELSE NULL END
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.task_key = 'verify_dates_of_birth';

DELETE rt
FROM request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.task_key IN ('verify_names_spellings', 'verify_email_phone');

UPDATE request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
SET rt.sort_order = rt.sort_order - 2
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.sort_order > 3;

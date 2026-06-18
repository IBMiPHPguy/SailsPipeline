UPDATE request_tasks rt
JOIN request_workflows rw ON rw.id = rt.request_workflow_id
SET rt.sort_order = rt.sort_order + 1
WHERE rw.workflow_type = 'enter_trip_crm'
  AND rt.sort_order >= 3;

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
    'create_cabin_holds',
    'Create cabin holds with cruise lines',
    'Enter cruise line reservation IDs for each cabin on this request.',
    'Open',
    3
FROM request_workflows rw
WHERE rw.workflow_type = 'enter_trip_crm'
  AND NOT EXISTS (
      SELECT 1
      FROM request_tasks existing
      WHERE existing.request_workflow_id = rw.id
        AND existing.task_key = 'create_cabin_holds'
  );

UPDATE request_tasks
SET
    task_key = 'collect_passenger_addresses',
    title = 'Collect passenger addresses',
    description = 'Collect the primary passenger''s home address. Other passenger addresses are optional.'
WHERE task_key = 'collect_lead_passenger_addresses';

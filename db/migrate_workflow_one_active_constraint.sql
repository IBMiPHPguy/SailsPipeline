-- Enforce at most one Active workflow per travel request (partial unique via generated column).
-- Safe to re-run: skips steps that already exist.

SET @has_column := (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'request_workflows_live'
      AND column_name = 'active_request_key'
);

SET @add_column_sql := IF(
    @has_column = 0,
    'ALTER TABLE request_workflows_live
        ADD COLUMN active_request_key INT GENERATED ALWAYS AS (
            IF(status = ''Active'', travel_request_id, NULL)
        ) STORED',
    'SELECT ''active_request_key already exists'' AS info'
);

PREPARE stmt FROM @add_column_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_index := (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'request_workflows_live'
      AND index_name = 'uq_request_workflows_live_one_active'
);

SET @add_index_sql := IF(
    @has_index = 0,
    'CREATE UNIQUE INDEX uq_request_workflows_live_one_active
        ON request_workflows_live (active_request_key)',
    'SELECT ''uq_request_workflows_live_one_active already exists'' AS info'
);

PREPARE stmt FROM @add_index_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

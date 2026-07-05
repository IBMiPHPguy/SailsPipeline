#!/usr/bin/env python3
"""Check workflow-related schema and data health (run on production via docker compose exec)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.database import SessionLocal


def _table_exists(db, table_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).one()
    return int(row.cnt) > 0


def _column_exists(db, table_name: str, column_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).one()
    return int(row.cnt) > 0


def _index_exists(db, table_name: str, index_name: str) -> bool:
    row = db.execute(
        text(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
              AND index_name = :index_name
            """
        ),
        {"table_name": table_name, "index_name": index_name},
    ).one()
    return int(row.cnt) > 0


def main() -> int:
    db = SessionLocal()
    ok = True
    try:
        checks = [
            ("agency_workflow_templates table", _table_exists(db, "agency_workflow_templates")),
            ("agency_task_templates table", _table_exists(db, "agency_task_templates")),
            ("request_workflows_live table", _table_exists(db, "request_workflows_live")),
            ("request_tasks_live table", _table_exists(db, "request_tasks_live")),
            ("agency_workflow_templates.archived_at", _column_exists(db, "agency_workflow_templates", "archived_at")),
            (
                "request_workflows_live.active_request_key",
                _column_exists(db, "request_workflows_live", "active_request_key"),
            ),
            (
                "uq_request_workflows_live_one_active index",
                _index_exists(db, "request_workflows_live", "uq_request_workflows_live_one_active"),
            ),
            (
                "agency_custom_task_definitions table",
                _table_exists(db, "agency_custom_task_definitions"),
            ),
        ]

        print("Schema checks:")
        for label, passed in checks:
            status = "OK" if passed else "FAIL"
            print(f"  [{status}] {label}")
            if not passed:
                ok = False

        if _table_exists(db, "agency_task_templates"):
            dup_rows = db.execute(
                text(
                    """
                    SELECT workflow_template_id, task_key, COUNT(*) AS cnt
                    FROM agency_task_templates
                    WHERE task_key IS NOT NULL
                    GROUP BY workflow_template_id, task_key
                    HAVING COUNT(*) > 1
                    ORDER BY cnt DESC
                    LIMIT 20
                    """
                )
            ).all()
            print("\nDuplicate template task_keys:")
            if not dup_rows:
                print("  OK — none found")
            else:
                ok = False
                for row in dup_rows:
                    print(f"  FAIL workflow={row.workflow_template_id} task_key={row.task_key} count={row.cnt}")

        if _table_exists(db, "request_workflows_live") and _column_exists(
            db, "request_workflows_live", "active_request_key"
        ):
            active_dup_rows = db.execute(
                text(
                    """
                    SELECT travel_request_id, COUNT(*) AS cnt
                    FROM request_workflows_live
                    WHERE status = 'Active'
                    GROUP BY travel_request_id
                    HAVING COUNT(*) > 1
                    """
                )
            ).all()
            print("\nRequests with multiple active workflows:")
            if not active_dup_rows:
                print("  OK — none found")
            else:
                ok = False
                for row in active_dup_rows:
                    print(f"  FAIL request_id={row.travel_request_id} active_count={row.cnt}")

        print("\nOverall:", "OK" if ok else "FAIL — run missing migrations and repair script")
        return 0 if ok else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

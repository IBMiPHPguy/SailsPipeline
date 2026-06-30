"""Seed agency workflow playbooks and migrate legacy request_workflows rows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.services.workflow_template_seed import migrate_legacy_workflows_to_live, seed_all_agency_workflow_templates


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed workflow playbooks and migrate legacy workflows.")
    parser.add_argument(
        "--skip-legacy-migration",
        action="store_true",
        help="Only seed agency templates; do not copy request_workflows into live tables.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_all_agency_workflow_templates(db)
        if not args.skip_legacy_migration:
            migrate_legacy_workflows_to_live(db)
        print("Workflow engine migration completed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

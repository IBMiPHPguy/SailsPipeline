#!/usr/bin/env python3
"""One-time repair: seed missing recommended workflow playbooks for existing agencies.

Run after tenants were provisioned before workflow seeding was added to onboarding.
Safe to re-run; only creates missing templates, backfills empty recommended playbooks,
and wires default successor links when absent.

Examples:
  docker compose exec backend python scripts/repair_agency_workflow_templates.py --dry-run
  docker compose exec backend python scripts/repair_agency_workflow_templates.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Agency, AgencyTaskTemplate, AgencyWorkflowTemplate
from app.workflow_helpers import WORKFLOW_DEFINITIONS, WORKFLOW_SUCCESSORS
from app.services.workflow_template_seed import (
    dedupe_workflow_template_task_keys,
    replace_workflow_template_tasks_with_defaults,
    seed_agency_workflow_templates,
    wire_default_successor_link,
    _workflow_template_task_count,
)


@dataclass(frozen=True)
class AgencyWorkflowSnapshot:
    active_template_count: int
    missing_recommended_types: tuple[str, ...]
    empty_recommended_types: tuple[str, ...]


def _snapshot_agency_workflows(db: Session, agency_id: str) -> AgencyWorkflowSnapshot:
    active_templates = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyWorkflowTemplate.archived_at.is_(None),
        )
        .all()
    )
    active_by_type = {
        template.workflow_type_key: template
        for template in active_templates
        if template.workflow_type_key
    }

    missing_recommended_types: list[str] = []
    empty_recommended_types: list[str] = []
    for workflow_type, definition in WORKFLOW_DEFINITIONS.items():
        template = active_by_type.get(workflow_type)
        if template is None:
            archived = (
                db.query(AgencyWorkflowTemplate)
                .filter(
                    AgencyWorkflowTemplate.agency_id == agency_id,
                    AgencyWorkflowTemplate.workflow_type_key == workflow_type,
                    AgencyWorkflowTemplate.archived_at.isnot(None),
                )
                .first()
            )
            if archived is None:
                missing_recommended_types.append(definition["name"])
            continue

        task_count = (
            db.query(AgencyTaskTemplate)
            .filter(AgencyTaskTemplate.workflow_template_id == template.id)
            .count()
        )
        if task_count == 0:
            empty_recommended_types.append(definition["name"])

    return AgencyWorkflowSnapshot(
        active_template_count=len(active_templates),
        missing_recommended_types=tuple(missing_recommended_types),
        empty_recommended_types=tuple(empty_recommended_types),
    )


def _backfill_empty_recommended_templates(db: Session, agency_id: str) -> list[str]:
    repaired: list[str] = []
    for workflow_type, definition in WORKFLOW_DEFINITIONS.items():
        template = (
            db.query(AgencyWorkflowTemplate)
            .filter(
                AgencyWorkflowTemplate.agency_id == agency_id,
                AgencyWorkflowTemplate.workflow_type_key == workflow_type,
                AgencyWorkflowTemplate.archived_at.is_(None),
            )
            .first()
        )
        if template is None:
            continue

        task_count = _workflow_template_task_count(db, template)
        if task_count > 0:
            continue

        replace_workflow_template_tasks_with_defaults(db, template, workflow_type)
        repaired.append(definition["name"])

    return repaired


def _wire_missing_successor_links(db: Session, agency_id: str) -> None:
    for workflow_type in WORKFLOW_SUCCESSORS:
        template = (
            db.query(AgencyWorkflowTemplate)
            .filter(
                AgencyWorkflowTemplate.agency_id == agency_id,
                AgencyWorkflowTemplate.workflow_type_key == workflow_type,
                AgencyWorkflowTemplate.archived_at.is_(None),
            )
            .first()
        )
        if template is None or template.successor_template_id is not None:
            continue
        wire_default_successor_link(
            db,
            agency_id=agency_id,
            workflow_template=template,
            workflow_type=workflow_type,
        )


def repair_agency_workflow_templates(db: Session, agency_id: str) -> None:
    seed_agency_workflow_templates(db, agency_id)
    _backfill_empty_recommended_templates(db, agency_id)
    _wire_missing_successor_links(db, agency_id)
    _dedupe_recommended_task_templates(db, agency_id)
    db.flush()


def _dedupe_recommended_task_templates(db: Session, agency_id: str) -> None:
    for workflow_type in WORKFLOW_DEFINITIONS:
        template = (
            db.query(AgencyWorkflowTemplate)
            .filter(
                AgencyWorkflowTemplate.agency_id == agency_id,
                AgencyWorkflowTemplate.workflow_type_key == workflow_type,
                AgencyWorkflowTemplate.archived_at.is_(None),
            )
            .first()
        )
        if template is None:
            continue
        dedupe_workflow_template_task_keys(db, template)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seed missing SailsPipeline recommended workflow playbooks for agencies "
            "provisioned before onboarding included workflow templates."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report agencies that need repair without writing changes.",
    )
    parser.add_argument(
        "--agency-id",
        metavar="UUID",
        help="Repair a single agency by id (default: all agencies).",
    )
    parser.add_argument(
        "--dedupe-all",
        action="store_true",
        help="Remove duplicate task_key rows from recommended workflows for every agency.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    db = SessionLocal()
    try:
        agency_query = db.query(Agency).order_by(Agency.organization_handle.asc())
        if args.agency_id:
            agency_query = agency_query.filter(Agency.id == args.agency_id)

        agencies = agency_query.all()
        if not agencies:
            print("No matching agencies found.", file=sys.stderr)
            return 1

        repaired_agencies = 0
        for agency in agencies:
            before = _snapshot_agency_workflows(db, agency.id)
            needs_repair = before.missing_recommended_types or before.empty_recommended_types
            if args.dedupe_all and not args.dry_run:
                print(f"{agency.organization_handle} ({agency.name})")
                print("  deduping recommended workflow tasks")
                _dedupe_recommended_task_templates(db, agency.id)
                repaired_agencies += 1
                continue

            if not needs_repair:
                continue

            print(f"{agency.organization_handle} ({agency.name})")
            if before.missing_recommended_types:
                print(f"  missing recommended: {', '.join(before.missing_recommended_types)}")
            if before.empty_recommended_types:
                print(f"  empty recommended: {', '.join(before.empty_recommended_types)}")

            if args.dry_run:
                repaired_agencies += 1
                continue

            repair_agency_workflow_templates(db, agency.id)
            after = _snapshot_agency_workflows(db, agency.id)
            print(f"  active templates after repair: {after.active_template_count}")
            repaired_agencies += 1

        if args.dry_run:
            if args.dedupe_all:
                print(f"\nDry run: would dedupe recommended tasks for {len(agencies)} agency/agencies.")
                return 0
            if repaired_agencies == 0:
                print("All agencies already have recommended workflow playbooks.")
            else:
                print(f"\nDry run: {repaired_agencies} agency/agencies would be repaired.")
            return 0

        if repaired_agencies == 0:
            if args.dedupe_all:
                print("No agencies found to dedupe.")
            else:
                print("All agencies already have recommended workflow playbooks.")
            return 0

        db.commit()
        if args.dedupe_all:
            print(f"\nDedupe complete for {repaired_agencies} agency/agencies.")
        else:
            print(f"\nRepair complete for {repaired_agencies} agency/agencies.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

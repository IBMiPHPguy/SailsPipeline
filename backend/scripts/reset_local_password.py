#!/usr/bin/env python3
"""Reset a tenant CRM user's password in local development only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal
from app.security import hash_password, validate_password
from app.services.auth_service import normalize_organization_handle, resolve_agency_by_organization_handle
from app.models import User


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reset a CRM user's password (development environments only)."
    )
    parser.add_argument("--organization-handle", required=True, help="Tenant organization handle")
    parser.add_argument("--username", required=True, help="CRM username")
    parser.add_argument("--password", required=True, help="New password")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if settings.app_env != "development":
        print("This script only runs when APP_ENV=development.", file=sys.stderr)
        return 1

    try:
        validate_password(args.password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        agency = resolve_agency_by_organization_handle(db, args.organization_handle)
        if agency is None:
            print(f"No active agency found for handle '{normalize_organization_handle(args.organization_handle)}'.", file=sys.stderr)
            return 1

        user = (
            db.query(User)
            .filter(
                User.username == args.username.strip(),
                User.agency_id == agency.id,
                User.is_active.is_(True),
            )
            .first()
        )
        if user is None:
            print(
                f"No active user '{args.username.strip()}' in agency '{agency.organization_handle}'.",
                file=sys.stderr,
            )
            return 1

        handle = agency.organization_handle
        user.password_hash = hash_password(args.password)
        db.commit()
    finally:
        db.close()

    print(f"Password updated for {args.username.strip()} @ {handle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

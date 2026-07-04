#!/usr/bin/env python3
"""One-time Bridge launch for new cloud deployments (schema verify + platform operator bootstrap)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal
from app.services.bridge_launch_service import BridgeLaunchError, run_bridge_launch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the SailsPipeline Bridge launch sequence on a fresh deployment. "
            "Verifies schema readiness and bootstraps the platform operator account. "
            "Does not seed tenant agencies."
        )
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify database connectivity and schema without creating or updating users.",
    )
    parser.add_argument(
        "--force-password",
        action="store_true",
        help="Reset the platform operator password when the launch username already exists.",
    )
    return parser


def _resolve_launch_credentials() -> tuple[str, str, str]:
    username = (settings.seed_bridge_admin_username or "").strip()
    password = settings.seed_bridge_admin_password or ""
    email = (settings.seed_bridge_admin_email or "").strip()

    if not username or not password:
        raise BridgeLaunchError(
            "Set SEED_BRIDGE_ADMIN_USERNAME and SEED_BRIDGE_ADMIN_PASSWORD in the environment "
            "before running Bridge launch."
        )

    if not email:
        email = f"{username}@example.com"

    return username, email, password


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        username, email, password = _resolve_launch_credentials()
        db = SessionLocal()
        try:
            report = run_bridge_launch(
                db,
                username=username,
                email=email,
                password=password,
                force_password_reset=args.force_password,
                check_only=args.check_only,
                public_registration_enabled=settings.allow_public_registration,
            )
        finally:
            db.close()
    except BridgeLaunchError as exc:
        print(f"Bridge launch failed: {exc}", file=sys.stderr)
        return 1

    if args.check_only:
        print("Bridge launch preflight passed.")
        print(f"- Schema tables: ready")
        print(f"- Platform operators: {report.platform_operator_count}")
        print(f"- Public registration: {'enabled' if report.public_registration_enabled else 'disabled'}")
        return 0

    action = "created" if report.platform_operator_created else "verified"
    print("Bridge launch complete.")
    print(f"- Database schema: ready")
    print(f"- Platform operator: {report.platform_operator_username} ({action})")
    print(f"- Platform operator count: {report.platform_operator_count}")
    print(f"- Tenant agencies seeded: none (onboarding is user-driven)")
    print(f"- Public self-service /register: {'enabled' if report.public_registration_enabled else 'disabled'}")
    print()
    print("Next steps:")
    print("1. Sign in to The Bridge at /bridge with the platform operator credentials.")
    print("2. Provision agencies via Bridge invitations (/onboarding) or enable ALLOW_PUBLIC_REGISTRATION for /register.")
    print("3. Confirm API health at /api/health.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

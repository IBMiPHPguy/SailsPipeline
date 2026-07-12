"""Idempotent startup DDL patches for databases created before the latest schema."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine


def migrate_agency_trial_period(db: Session) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("agencies")}
    if "trial_ends_at" in columns:
        return

    db.execute(
        text(
            "ALTER TABLE agencies "
            "ADD COLUMN trial_ends_at TIMESTAMP NULL AFTER subscription_state"
        )
    )
    db.execute(text("CREATE INDEX idx_agencies_trial_ends_at ON agencies (trial_ends_at)"))
    db.commit()


def migrate_password_reset_columns(db: Session) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "reset_token_hash" in columns and "reset_token_expires_at" in columns:
        return

    if "reset_token_hash" not in columns:
        db.execute(
            text("ALTER TABLE users ADD COLUMN reset_token_hash VARCHAR(255) NULL AFTER password_hash")
        )
    if "reset_token_expires_at" not in columns:
        db.execute(
            text(
                "ALTER TABLE users ADD COLUMN reset_token_expires_at DATETIME NULL "
                "AFTER reset_token_hash"
            )
        )
    db.commit()


def migrate_user_profile_columns(db: Session) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "avatar_url" in columns and "email_signature_block" in columns:
        return

    if "avatar_url" not in columns:
        db.execute(
            text(
                "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(1024) NULL "
                "AFTER can_view_all_agency_leads"
            )
        )
    if "email_signature_block" not in columns:
        db.execute(
            text(
                "ALTER TABLE users ADD COLUMN email_signature_block TEXT NULL "
                "AFTER avatar_url"
            )
        )
    db.commit()


def run_startup_schema_migrations(db: Session) -> None:
    """Apply schema reconciliation only. Never inserts tenants, users, or seed rows."""
    migrate_agency_trial_period(db)
    migrate_password_reset_columns(db)
    migrate_user_profile_columns(db)

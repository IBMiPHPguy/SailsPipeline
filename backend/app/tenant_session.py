"""Backward-compatible re-export; tenant query filtering lives in app.database."""

from app.database import TENANT_SCOPED_MODELS, configure_tenant_session

__all__ = ["TENANT_SCOPED_MODELS", "configure_tenant_session"]

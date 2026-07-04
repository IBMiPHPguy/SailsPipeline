from __future__ import annotations

from contextvars import ContextVar

_current_agency_id: ContextVar[str | None] = ContextVar("current_agency_id", default=None)
_tenant_scoping_required: ContextVar[bool] = ContextVar("tenant_scoping_required", default=False)


class TenantContextRequiredError(RuntimeError):
    """Raised when a CRM route queries tenant-scoped ORM data without agency_id in context."""


def get_current_agency_id() -> str | None:
    return _current_agency_id.get()


def set_current_agency_id(agency_id: str | None) -> None:
    _current_agency_id.set(agency_id)


def is_tenant_scoping_required() -> bool:
    return _tenant_scoping_required.get()


def set_tenant_scoping_required(required: bool) -> None:
    _tenant_scoping_required.set(required)


def clear_current_agency_id() -> None:
    _current_agency_id.set(None)


def clear_tenant_request_context() -> None:
    """Reset per-request tenant bindings (agency id and scoping flag)."""
    _current_agency_id.set(None)
    _tenant_scoping_required.set(False)


def require_current_agency_id() -> str:
    agency_id = get_current_agency_id()
    if agency_id is None:
        raise TenantContextRequiredError("Tenant context is not set.")
    return agency_id

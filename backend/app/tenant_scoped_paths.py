"""HTTP path rules for fail-closed tenant ORM scoping on authenticated CRM routes."""

from __future__ import annotations

from app.openapi_paths import is_openapi_documentation_path

TENANT_SCOPING_EXEMPT_PREFIXES = (
    "/api/health",
    "/api/auth/",
    "/api/onboarding/",
    "/api/bridge/",
    "/api/cc-auth/",
    "/api/terms/",
    "/api/insurance/",
    "/api/public/",
)


def requires_tenant_scoping_for_path(path: str) -> bool:
    """Return True when /api CRM handlers must bind agency_id before tenant-scoped ORM access."""
    if is_openapi_documentation_path(path):
        return False
    if not path.startswith("/api/"):
        return False
    return not any(path.startswith(prefix) for prefix in TENANT_SCOPING_EXEMPT_PREFIXES)

"""Paths for local OpenAPI / Swagger documentation that must bypass tenant middleware."""

OPENAPI_DOCUMENTATION_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static/swaggerui",
)


def is_openapi_documentation_path(path: str) -> bool:
    """Return True for Swagger UI, ReDoc, schema JSON, and bundled doc assets."""
    normalized = path.rstrip("/") or "/"
    if normalized == "/openapi.json":
        return True
    return any(
        normalized == prefix.rstrip("/") or path.startswith(f"{prefix.rstrip('/')}/")
        for prefix in OPENAPI_DOCUMENTATION_PREFIXES
        if prefix != "/openapi.json"
    )

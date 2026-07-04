import pytest

from app.openapi_paths import is_openapi_documentation_path


@pytest.mark.parametrize(
    "path",
    [
        "/docs",
        "/docs/",
        "/docs/oauth2-redirect",
        "/redoc",
        "/openapi.json",
        "/static/swaggerui/swagger-ui-bundle.js",
        "/static/swaggerui/swagger-ui.css",
    ],
)
def test_is_openapi_documentation_path_matches_doc_routes(path: str):
    assert is_openapi_documentation_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "/api/health",
        "/api/dashboard",
        "/api/auth/login",
        "/static/uploads/logo_agency_abc.png",
        "/",
    ],
)
def test_is_openapi_documentation_path_rejects_operational_routes(path: str):
    assert is_openapi_documentation_path(path) is False

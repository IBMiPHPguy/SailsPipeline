from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.openapi_paths import is_openapi_documentation_path
from app.security import decode_access_token
from app.tenant_context import (
    clear_tenant_request_context,
    set_current_agency_id,
    set_tenant_scoping_required,
)
from app.tenant_scoped_paths import requires_tenant_scoping_for_path


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract agency_id from a validated JWT and bind it to the request context."""

    async def dispatch(self, request: Request, call_next) -> Response:
        clear_tenant_request_context()
        request.state.agency_id = None

        path = request.url.path
        set_tenant_scoping_required(requires_tenant_scoping_for_path(path))

        if not is_openapi_documentation_path(path):
            auth_header = request.headers.get("Authorization", "")
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:].strip()
                if token:
                    try:
                        claims = decode_access_token(token)
                        if claims.agency_id is not None:
                            set_current_agency_id(claims.agency_id)
                            request.state.agency_id = claims.agency_id
                    except ValueError:
                        pass

        try:
            return await call_next(request)
        finally:
            clear_tenant_request_context()
            request.state.agency_id = None

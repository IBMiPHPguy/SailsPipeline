from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.openapi_paths import is_openapi_documentation_path
from app.security import decode_access_token
from app.tenant_context import clear_current_agency_id, set_current_agency_id


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Extract agency_id from a validated JWT and bind it to the request context."""

    async def dispatch(self, request: Request, call_next) -> Response:
        clear_current_agency_id()
        request.state.agency_id = None

        if not is_openapi_documentation_path(request.url.path):
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
            clear_current_agency_id()
            request.state.agency_id = None

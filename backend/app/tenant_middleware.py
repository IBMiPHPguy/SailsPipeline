from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.security import decode_access_token
from app.tenant_context import clear_current_agency_id, set_current_agency_id


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Set tenant context from JWT before sync route handlers run in worker threads."""

    async def dispatch(self, request: Request, call_next) -> Response:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    claims = decode_access_token(token)
                    set_current_agency_id(claims.agency_id)
                except ValueError:
                    pass

        try:
            return await call_next(request)
        finally:
            clear_current_agency_id()

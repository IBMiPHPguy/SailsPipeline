from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.database import SessionLocal
from app.models import Agency
from app.security import decode_access_token
from app.services.subscription_service import (
    build_subscription_block_payload,
    enforce_trial_expiration,
)
from app.tenant_roles import SUBSCRIPTION_STATE_LOCKED, SUBSCRIPTION_STATE_PAST_DUE

SUBSCRIPTION_EXEMPT_PREFIXES = (
    "/api/health",
    "/api/auth/",
    "/api/onboarding/",
    "/api/bridge/",
    "/api/cc-auth/",
    "/api/terms/",
    "/api/insurance/",
    "/api/public/",
)

BLOCKED_SUBSCRIPTION_STATES = {
    SUBSCRIPTION_STATE_LOCKED,
    SUBSCRIPTION_STATE_PAST_DUE,
}


class SubscriptionGatekeeperMiddleware(BaseHTTPMiddleware):
    """Block operational CRM API access when a tenant subscription is past due or locked."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
        if any(path.startswith(prefix) for prefix in SUBSCRIPTION_EXEMPT_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return await call_next(request)

        token = auth_header[7:].strip()
        if not token:
            return await call_next(request)

        try:
            claims = decode_access_token(token)
        except ValueError:
            return await call_next(request)

        if claims.agency_id is None:
            return await call_next(request)

        db = SessionLocal()
        try:
            agency = db.get(Agency, claims.agency_id)
            if agency is not None:
                enforce_trial_expiration(db, agency)
                db.refresh(agency)
            if agency is not None and agency.subscription_state in BLOCKED_SUBSCRIPTION_STATES:
                block_payload = build_subscription_block_payload(agency)
                return JSONResponse(
                    status_code=402,
                    content={
                        "detail": block_payload["message"],
                        "subscription_state": block_payload["subscription_state"],
                        **(
                            {"lock_reason": block_payload["lock_reason"]}
                            if "lock_reason" in block_payload
                            else {}
                        ),
                    },
                )
        finally:
            db.close()

        return await call_next(request)

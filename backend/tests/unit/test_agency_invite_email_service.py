from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models import AgencyInvitation
from app.services.agency_invite_email_service import (
    AGENCY_INVITE_EMAIL_TYPE,
    dispatch_agency_invite_email,
    render_agency_invite_email_html,
)
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_roles import USER_ROLE_TENANT_AGENT


@pytest.mark.unit
def test_render_agency_invite_email_html_includes_invite_link(db, test_user):
    from app.models import Agency

    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    invitation = AgencyInvitation(
        id="invite-test-id",
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="joiner@example.com",
        token="sample-token-value",
        role=USER_ROLE_TENANT_AGENT,
        is_used=False,
        expires_at=agency.created_at,
    )
    invite_url = "http://localhost:8080/register-agent?token=sample-token-value"

    from app.agency_email_branding import load_agency_email_branding

    branding = load_agency_email_branding(db, agency_id=DEFAULT_AGENCY_ID)
    html = render_agency_invite_email_html(
        branding=branding,
        agency=agency,
        inviting_user=test_user,
        invitation=invitation,
        invite_url=invite_url,
    )

    assert "joiner@example.com" in html
    assert invite_url in html
    assert branding.agency_name in html
    assert "Your travel advisor" not in html
    assert agency.organization_handle in html
    assert "Testuser" in html
    assert test_user.username not in html


@pytest.mark.unit
@patch("app.services.agency_invite_email_service.EmailDeliveryService.send_transactional_email", new_callable=AsyncMock)
def test_dispatch_agency_invite_email_passes_tenant_context(mock_send, db, test_user):
    from app.models import Agency

    mock_send.return_value = True
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    invitation = AgencyInvitation(
        id="invite-dispatch-id",
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="joiner@example.com",
        token="dispatch-token",
        role=USER_ROLE_TENANT_AGENT,
        is_used=False,
        expires_at=agency.created_at,
    )

    asyncio.run(
        dispatch_agency_invite_email(
            db,
            agency=agency,
            inviting_user=test_user,
            invitation=invitation,
        )
    )

    mock_send.assert_awaited_once()
    kwargs = mock_send.await_args.kwargs
    assert kwargs["agency_name"]
    assert kwargs["agent_email"] == test_user.email
    assert kwargs["recipient"] == "joiner@example.com"
    assert kwargs["email_type"] == AGENCY_INVITE_EMAIL_TYPE
    assert "register-agent?token=dispatch-token" in kwargs["html_content"]


@pytest.mark.unit
@patch("app.services.agency_invite_email_service.EmailDeliveryService.send_transactional_email", new_callable=AsyncMock)
def test_dispatch_agency_invite_email_raises_when_delivery_fails(mock_send, db, test_user):
    from app.models import Agency

    mock_send.return_value = False
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    invitation = AgencyInvitation(
        id="invite-fail-id",
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="joiner@example.com",
        token="fail-token",
        role=USER_ROLE_TENANT_AGENT,
        is_used=False,
        expires_at=agency.created_at,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            dispatch_agency_invite_email(
                db,
                agency=agency,
                inviting_user=test_user,
                invitation=invitation,
            )
        )

    assert exc.value.status_code == 502

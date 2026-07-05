from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models import PlatformInvitation, User
from app.security import hash_password
from app.services.platform_invite_email_service import (
    PLATFORM_INVITE_EMAIL_TYPE,
    dispatch_platform_invite_email,
    render_platform_invite_email_html,
)
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN


def _bridge_admin_user(db) -> User:
    user = User(
        agency_id=None,
        username="bridgeadmin",
        email="bridgeadmin@example.com",
        password_hash=hash_password("BridgePass1!"),
        role=USER_ROLE_PLATFORM_SUPER_ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.mark.unit
def test_render_platform_invite_email_html_includes_onboarding_link(db):
    bridge_admin_user = _bridge_admin_user(db)
    invitation = PlatformInvitation(
        id="platform-invite-test",
        target_agency_name="Harbor Lights Travel",
        target_organization_handle="harborlights",
        invite_email="owner@harborlights.example",
        token="platform-token",
        is_used=False,
        expires_at=bridge_admin_user.created_at,
    )
    invite_url = "http://localhost:8080/onboarding?token=platform-token"

    from app.services.platform_invite_email_service import _onboarding_branding

    branding = _onboarding_branding(invitation)
    html = render_platform_invite_email_html(
        branding=branding,
        invitation=invitation,
        inviting_user=bridge_admin_user,
        invite_url=invite_url,
    )

    assert "Harbor Lights Travel" in html
    assert "harborlights" in html
    assert invite_url in html
    assert "owner@harborlights.example" in html


@pytest.mark.unit
@patch("app.services.platform_invite_email_service.EmailDeliveryService.send_transactional_email", new_callable=AsyncMock)
def test_dispatch_platform_invite_email_passes_tenant_context(mock_send, db):
    bridge_admin_user = _bridge_admin_user(db)
    mock_send.return_value = True
    invitation = PlatformInvitation(
        id="platform-dispatch-test",
        target_agency_name="Harbor Lights Travel",
        target_organization_handle="harborlights",
        invite_email="owner@harborlights.example",
        token="dispatch-token",
        is_used=False,
        expires_at=bridge_admin_user.created_at,
    )

    asyncio.run(
        dispatch_platform_invite_email(
            db,
            inviting_user=bridge_admin_user,
            invitation=invitation,
        )
    )

    mock_send.assert_awaited_once()
    kwargs = mock_send.await_args.kwargs
    assert kwargs["agency_name"] == "Harbor Lights Travel"
    assert kwargs["agent_email"] == bridge_admin_user.email
    assert kwargs["recipient"] == "owner@harborlights.example"
    assert kwargs["email_type"] == PLATFORM_INVITE_EMAIL_TYPE
    assert "onboarding?token=dispatch-token" in kwargs["html_content"]


@pytest.mark.unit
@patch("app.services.platform_invite_email_service.EmailDeliveryService.send_transactional_email", new_callable=AsyncMock)
def test_dispatch_platform_invite_email_raises_when_delivery_fails(mock_send, db):
    bridge_admin_user = _bridge_admin_user(db)
    mock_send.return_value = False
    invitation = PlatformInvitation(
        id="platform-fail-test",
        target_agency_name="Harbor Lights Travel",
        target_organization_handle="harborlights",
        invite_email="owner@harborlights.example",
        token="fail-token",
        is_used=False,
        expires_at=bridge_admin_user.created_at,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            dispatch_platform_invite_email(
                db,
                inviting_user=bridge_admin_user,
                invitation=invitation,
            )
        )

    assert exc.value.status_code == 502

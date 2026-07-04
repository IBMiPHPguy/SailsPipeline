"""Unit tests for public registration anonymization and global DB error sanitization."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request

from app.application import create_app
from app.services.public_registration_service import (
    PUBLIC_REGISTRATION_SUCCESS_MESSAGE,
    PublicRegistrationUnavailableError,
    register_public_tenant,
)


def test_register_public_tenant_raises_unavailable_for_duplicate_email(db, test_user):
    register_public_tenant(
        db,
        agency_name="Alpha Travel",
        admin_email="shared@example.com",
        admin_name="Casey Lane",
        password="AgencyPass1!",
    )

    with pytest.raises(PublicRegistrationUnavailableError):
        register_public_tenant(
            db,
            agency_name="Beta Travel",
            admin_email="shared@example.com",
            admin_name="Casey Lane",
            password="AgencyPass1!",
        )


def test_public_register_route_returns_generic_message_for_duplicate(client, db, test_user):
    payload = {
        "agency_name": "Gamma Travel",
        "admin_name": "Dana Fox",
        "admin_email": "dana@example.com",
        "password": "AgencyPass1!",
    }
    first = client.post("/api/public/register", json=payload)
    assert first.status_code == 201, first.text

    second = client.post("/api/public/register", json=payload)
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["message"] == PUBLIC_REGISTRATION_SUCCESS_MESSAGE
    assert "access_token" not in body


def test_sqlalchemy_error_handler_returns_sanitized_response():
    application = create_app()
    handler = application.exception_handlers.get(SQLAlchemyError)
    assert handler is not None

    request = Request(
        scope={
            "type": "http",
            "method": "GET",
            "path": "/api/requests",
            "headers": [],
        }
    )
    response = asyncio.run(handler(request, SQLAlchemyError("relation secret_table does not exist")))

    assert response.status_code == 500
    assert response.body == b'{"detail":"Internal server error."}'

import pytest
from fastapi import HTTPException

from app.attachment_storage import resolve_attachment_path, write_bytes
from app.config import Settings
from app.security_config import validate_production_settings
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_scoped_paths import requires_tenant_scoping_for_path


def test_validate_production_settings_rejects_insecure_defaults():
    settings = Settings(
        app_env="production",
        jwt_secret="change-me-in-production",
        database_url="mysql+pymysql://cruiseapp:cruisesecret@db:3306/sailspipeline",
        allow_public_registration=True,
        cors_origins="*",
        expose_openapi=True,
    )

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_settings(settings)


def test_validate_production_settings_accepts_secure_configuration():
    settings = Settings(
        app_env="production",
        jwt_secret="x" * 32,
        database_url="mysql+pymysql://appuser:K7mPq2vL9nR4wX8z@db:3306/sailspipeline",
        allow_public_registration=False,
        cors_origins="https://sailspipeline.com,https://app.sailspipeline.com",
        expose_openapi=False,
        email_api_key="re_live_production_key",
    )

    validate_production_settings(settings)


def test_validate_production_settings_rejects_http_cors_origin():
    settings = Settings(
        app_env="production",
        jwt_secret="x" * 32,
        database_url="mysql+pymysql://appuser:K7mPq2vL9nR4wX8z@db:3306/sailspipeline",
        allow_public_registration=False,
        cors_origins="http://sailspipeline.com",
        expose_openapi=False,
        email_api_key="re_live_production_key",
    )

    with pytest.raises(RuntimeError, match="https://"):
        validate_production_settings(settings)


def test_validate_production_settings_rejects_localhost_cors_origin():
    settings = Settings(
        app_env="production",
        jwt_secret="x" * 32,
        database_url="mysql+pymysql://appuser:K7mPq2vL9nR4wX8z@db:3306/sailspipeline",
        allow_public_registration=False,
        cors_origins="https://localhost",
        expose_openapi=False,
        email_api_key="re_live_production_key",
    )

    with pytest.raises(RuntimeError, match="localhost"):
        validate_production_settings(settings)


def test_validate_production_settings_requires_sailspipeline_domains():
    settings = Settings(
        app_env="production",
        jwt_secret="x" * 32,
        database_url="mysql+pymysql://appuser:K7mPq2vL9nR4wX8z@db:3306/sailspipeline",
        allow_public_registration=False,
        cors_origins="https://sailspipeline.example",
        expose_openapi=False,
        email_api_key="re_live_production_key",
    )

    with pytest.raises(RuntimeError, match="app.sailspipeline.com"):
        validate_production_settings(settings)


def test_requires_tenant_scoping_for_crm_api_paths():
    assert requires_tenant_scoping_for_path("/api/requests") is True
    assert requires_tenant_scoping_for_path("/api/passengers/1") is True


def test_tenant_scoping_exempt_public_and_portal_paths():
    assert requires_tenant_scoping_for_path("/api/public/register") is False
    assert requires_tenant_scoping_for_path("/api/cc-auth/validate/token") is False
    assert requires_tenant_scoping_for_path("/api/terms/validate/token") is False
    assert requires_tenant_scoping_for_path("/api/bridge/agencies") is False
    assert requires_tenant_scoping_for_path("/openapi.json") is False


def test_validate_production_settings_skips_non_production():
    settings = Settings(
        app_env="development",
        jwt_secret="change-me-in-production",
        allow_public_registration=True,
    )

    validate_production_settings(settings)


def test_resolve_attachment_path_rejects_traversal(tmp_path):
    attachments_dir = str(tmp_path)

    with pytest.raises(HTTPException, match="Invalid attachment path"):
        resolve_attachment_path(attachments_dir, "../outside.txt")


def test_resolve_attachment_path_rejects_absolute_path(tmp_path):
    attachments_dir = str(tmp_path)

    with pytest.raises(HTTPException, match="Invalid attachment path"):
        resolve_attachment_path(attachments_dir, "/etc/passwd")


def test_resolve_attachment_path_allows_files_under_root(tmp_path):
    attachments_dir = str(tmp_path)
    relative_path = f"{DEFAULT_AGENCY_ID}/requests/1/transcripts/demo.txt"

    write_bytes(attachments_dir, relative_path, b"hello", agency_id=DEFAULT_AGENCY_ID)
    target = resolve_attachment_path(attachments_dir, relative_path, agency_id=DEFAULT_AGENCY_ID)

    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "hello"


def test_resolve_attachment_path_rejects_wrong_agency_prefix(tmp_path):
    attachments_dir = str(tmp_path)
    relative_path = f"{DEFAULT_AGENCY_ID}/requests/1/transcripts/demo.txt"
    write_bytes(attachments_dir, relative_path, b"hello", agency_id=DEFAULT_AGENCY_ID)

    with pytest.raises(HTTPException, match="Attachment not found"):
        resolve_attachment_path(
            attachments_dir,
            relative_path,
            agency_id="00000000-0000-4000-8000-000000000002",
        )

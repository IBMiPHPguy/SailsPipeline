import pytest
from fastapi import HTTPException

from app.attachment_storage import resolve_attachment_path, write_bytes
from app.config import Settings
from app.security_config import validate_production_settings


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
        cors_origins="https://sailspipeline.example",
        expose_openapi=False,
    )

    validate_production_settings(settings)


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
    relative_path = "requests/1/transcripts/demo.txt"

    write_bytes(attachments_dir, relative_path, b"hello")
    target = resolve_attachment_path(attachments_dir, relative_path)

    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "hello"

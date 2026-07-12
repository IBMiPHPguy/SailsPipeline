from __future__ import annotations

import base64
import binascii
import logging
import os
import re
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
_CONTENT_TYPE_EXTENSION = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}
_INLINE_DATA_URL_PATTERN = re.compile(
    r"data:image/([^;]+);base64,([^\"'\s)>]+)",
    re.IGNORECASE,
)
_MAX_SIGNATURE_IMAGE_BYTES = 5 * 1024 * 1024


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_upload_extension(filename: str | None, content_type: str | None) -> str:
    if filename:
        suffix = Path(filename).suffix.lstrip(".").lower()
        if suffix in _ALLOWED_EXTENSIONS:
            return "jpg" if suffix == "jpeg" else suffix
    if content_type:
        mapped = _CONTENT_TYPE_EXTENSION.get(content_type.split(";")[0].strip().lower())
        if mapped:
            return mapped
    return "png"


def _sanitize_agency_token(agency_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", agency_id)


def _local_uploads_dir() -> Path:
    configured = Path(settings.brand_uploads_dir)
    if configured.is_absolute():
        return configured
    return _backend_root() / configured


def _save_local_asset(content: bytes, filename: str) -> str:
    uploads_dir = _local_uploads_dir()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    target = uploads_dir / filename
    target.write_bytes(content)
    return f"/static/uploads/{filename}"


def _save_local_logo(agency_id: str, content: bytes, extension: str) -> str:
    safe_agency = _sanitize_agency_token(agency_id)
    filename = f"logo_agency_{safe_agency}.{extension}"
    return _save_local_asset(content, filename)


def _upload_asset_to_s3(
    agency_id: str,
    content: bytes,
    content_type: str,
    extension: str,
    *,
    object_key: str,
) -> str:
    """Stream static agency assets to object storage in stage/prod deployments."""
    bucket = settings.s3_brand_bucket
    if not bucket:
        raise ValueError("S3_BRAND_BUCKET must be configured for stage/prod asset uploads.")

    # import boto3
    #
    # session = boto3.session.Session(region_name=settings.s3_brand_region)
    # client = session.client("s3")
    # client.put_object(
    #     Bucket=bucket,
    #     Key=object_key,
    #     Body=content,
    #     ContentType=content_type or f"image/{extension}",
    #     ACL="public-read",
    # )
    # base_url = (settings.s3_brand_public_base_url or f"https://{bucket}.s3.amazonaws.com").rstrip("/")
    # return f"{base_url}/{object_key}"

    raise NotImplementedError(
        "S3 asset upload is scaffolded for stage/prod. Configure S3_BRAND_BUCKET and enable boto3 upload."
    )


def _upload_logo_to_s3(agency_id: str, content: bytes, content_type: str, extension: str) -> str:
    safe_agency = _sanitize_agency_token(agency_id)
    object_key = f"brand-logos/logo_agency_{safe_agency}.{extension}"
    return _upload_asset_to_s3(
        agency_id,
        content,
        content_type,
        extension,
        object_key=object_key,
    )


def _upload_signature_image_to_s3(agency_id: str, content: bytes, content_type: str, extension: str, filename: str) -> str:
    object_key = f"signature-images/{filename}"
    return _upload_asset_to_s3(
        agency_id,
        content,
        content_type,
        extension,
        object_key=object_key,
    )


_LOCAL_LOGO_URL_MARKER = "/static/uploads/logo_agency_"


def resolve_local_upload_path_from_url(asset_url: str | None) -> Path | None:
    """Map a hosted /static/uploads/... URL back to an on-disk uploads path."""
    if not asset_url or _LOCAL_LOGO_URL_MARKER not in asset_url:
        return None

    filename = asset_url.rsplit("/", 1)[-1]
    if not filename.startswith("logo_agency_"):
        return None

    return _local_uploads_dir() / filename


def purge_stale_local_brand_logo(brand_logo_url: str | None) -> None:
    """Remove a superseded local agency logo file before replacing it."""
    local_path = resolve_local_upload_path_from_url(brand_logo_url)
    if local_path is None or not local_path.is_file():
        return

    try:
        os.remove(local_path)
    except OSError as exc:
        logger.warning("Unable to purge stale brand logo at %s: %s", local_path, exc)


def upload_agency_logo(
    agency_id: str,
    content: bytes,
    *,
    filename: str | None,
    content_type: str | None,
) -> str:
    extension = resolve_upload_extension(filename, content_type)
    if settings.uses_local_brand_uploads:
        return _save_local_logo(agency_id, content, extension)
    return _upload_logo_to_s3(
        agency_id,
        content,
        content_type or f"image/{extension}",
        extension,
    )


def upload_agency_signature_image(
    agency_id: str,
    content: bytes,
    *,
    filename: str | None,
    content_type: str | None,
) -> str:
    if len(content) > _MAX_SIGNATURE_IMAGE_BYTES:
        raise ValueError("Signature image must be 5 MB or smaller.")

    extension = resolve_upload_extension(filename, content_type)
    safe_agency = _sanitize_agency_token(agency_id)
    asset_filename = f"signature_{safe_agency}_{uuid.uuid4().hex[:12]}.{extension}"
    if settings.uses_local_brand_uploads:
        return _save_local_asset(content, asset_filename)
    return _upload_signature_image_to_s3(
        agency_id,
        content,
        content_type or f"image/{extension}",
        extension,
        asset_filename,
    )


def upload_user_avatar(
    user_id: int,
    content: bytes,
    *,
    filename: str | None,
    content_type: str | None,
    agency_id: str | None = None,
) -> str:
    if len(content) > _MAX_SIGNATURE_IMAGE_BYTES:
        raise ValueError("Avatar image must be 5 MB or smaller.")

    extension = resolve_upload_extension(filename, content_type)
    asset_filename = f"avatar_user_{user_id}_{uuid.uuid4().hex[:12]}.{extension}"
    if settings.uses_local_brand_uploads:
        return _save_local_asset(content, asset_filename)

    safe_agency = _sanitize_agency_token(agency_id or "platform")
    object_key = f"user-avatars/{safe_agency}/{asset_filename}"
    return _upload_asset_to_s3(
        agency_id or "platform",
        content,
        content_type or f"image/{extension}",
        extension,
        object_key=object_key,
    )


def upload_user_signature_image(
    user_id: int,
    content: bytes,
    *,
    filename: str | None,
    content_type: str | None,
    agency_id: str | None = None,
) -> str:
    if len(content) > _MAX_SIGNATURE_IMAGE_BYTES:
        raise ValueError("Signature image must be 5 MB or smaller.")

    extension = resolve_upload_extension(filename, content_type)
    asset_filename = f"signature_user_{user_id}_{uuid.uuid4().hex[:12]}.{extension}"
    if settings.uses_local_brand_uploads:
        return _save_local_asset(content, asset_filename)

    safe_agency = _sanitize_agency_token(agency_id or "platform")
    object_key = f"user-signature-images/{safe_agency}/{asset_filename}"
    return _upload_asset_to_s3(
        agency_id or "platform",
        content,
        content_type or f"image/{extension}",
        extension,
        object_key=object_key,
    )


def purge_stale_local_user_avatar(avatar_url: str | None) -> None:
    """Remove a superseded local avatar file before replacing it."""
    if not avatar_url or "/static/uploads/" not in avatar_url:
        return
    filename = avatar_url.rsplit("/", 1)[-1]
    if not filename.startswith("avatar_user_"):
        return
    local_path = _local_uploads_dir() / filename
    if not local_path.is_file():
        return
    try:
        os.remove(local_path)
    except OSError as exc:
        logger.warning("Unable to purge stale avatar at %s: %s", local_path, exc)


def externalize_inline_signature_images(agency_id: str, html: str | None) -> str | None:
    """Replace inline data-URI images with hosted static URLs to keep signatures storable."""
    if not html or "data:image" not in html:
        return html

    def replace_data_url(match: re.Match[str]) -> str:
        mime = match.group(1).lower()
        extension = "jpg" if mime in {"jpeg", "jpg"} else mime.split("+")[0]
        if extension not in _ALLOWED_EXTENSIONS:
            extension = "png"
        try:
            raw = base64.b64decode(match.group(2), validate=False)
        except (binascii.Error, ValueError):
            return match.group(0)
        if not raw:
            return match.group(0)
        try:
            return upload_agency_signature_image(
                agency_id,
                raw,
                filename=f"inline.{extension}",
                content_type=f"image/{extension}",
            )
        except (ValueError, NotImplementedError) as exc:
            logger.warning("Skipped inline signature image externalization: %s", exc)
            return match.group(0)

    return _INLINE_DATA_URL_PATTERN.sub(replace_data_url, html)


def externalize_inline_user_signature_images(
    user_id: int,
    html: str | None,
    *,
    agency_id: str | None = None,
) -> str | None:
    """Replace inline data-URI images with hosted URLs for a user's email signature."""
    if not html or "data:image" not in html:
        return html

    def replace_data_url(match: re.Match[str]) -> str:
        mime = match.group(1).lower()
        extension = "jpg" if mime in {"jpeg", "jpg"} else mime.split("+")[0]
        if extension not in _ALLOWED_EXTENSIONS:
            extension = "png"
        try:
            raw = base64.b64decode(match.group(2), validate=False)
        except (binascii.Error, ValueError):
            return match.group(0)
        if not raw:
            return match.group(0)
        try:
            return upload_user_signature_image(
                user_id,
                raw,
                filename=f"inline.{extension}",
                content_type=f"image/{extension}",
                agency_id=agency_id,
            )
        except (ValueError, NotImplementedError) as exc:
            logger.warning("Skipped inline user signature image externalization: %s", exc)
            return match.group(0)

    return _INLINE_DATA_URL_PATTERN.sub(replace_data_url, html)
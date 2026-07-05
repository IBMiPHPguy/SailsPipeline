from __future__ import annotations

from app.constants import INTAKE_MODE_SOCIAL_MEDIA, INTAKE_MODES, SOCIAL_MEDIA_PLATFORMS


def normalize_intake_attribution(
    *,
    intake_mode: str | None,
    intake_social_platform: str | None,
) -> tuple[str | None, str | None]:
    if intake_mode is None or not str(intake_mode).strip():
        return None, None

    normalized_mode = intake_mode.strip()
    if normalized_mode not in INTAKE_MODES:
        raise ValueError("Invalid intake mode selected.")

    if normalized_mode == INTAKE_MODE_SOCIAL_MEDIA:
        platform = (intake_social_platform or "").strip()
        if not platform:
            raise ValueError("Select a social media platform.")
        if platform not in SOCIAL_MEDIA_PLATFORMS:
            raise ValueError("Invalid social media platform selected.")
        return normalized_mode, platform

    return normalized_mode, None

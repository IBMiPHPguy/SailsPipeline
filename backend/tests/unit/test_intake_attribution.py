import pytest

from app.constants import INTAKE_MODE_EMAIL, INTAKE_MODE_SOCIAL_MEDIA, SOCIAL_MEDIA_FACEBOOK
from app.intake_attribution import normalize_intake_attribution


def test_normalize_intake_attribution_clears_empty_values():
    mode, platform = normalize_intake_attribution(intake_mode="", intake_social_platform="")
    assert mode is None
    assert platform is None


def test_normalize_intake_attribution_accepts_email_mode():
    mode, platform = normalize_intake_attribution(
        intake_mode=INTAKE_MODE_EMAIL,
        intake_social_platform=None,
    )
    assert mode == INTAKE_MODE_EMAIL
    assert platform is None


def test_normalize_intake_attribution_requires_social_platform():
    with pytest.raises(ValueError, match="social media platform"):
        normalize_intake_attribution(
            intake_mode=INTAKE_MODE_SOCIAL_MEDIA,
            intake_social_platform="",
        )


def test_normalize_intake_attribution_accepts_social_platform():
    mode, platform = normalize_intake_attribution(
        intake_mode=INTAKE_MODE_SOCIAL_MEDIA,
        intake_social_platform=SOCIAL_MEDIA_FACEBOOK,
    )
    assert mode == INTAKE_MODE_SOCIAL_MEDIA
    assert platform == SOCIAL_MEDIA_FACEBOOK

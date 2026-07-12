from app.config import Settings


def test_uses_local_brand_uploads_in_development():
    settings = Settings(app_env="development", s3_brand_bucket=None)
    assert settings.uses_local_brand_uploads is True


def test_uses_local_brand_uploads_in_production_without_s3_bucket():
    settings = Settings(app_env="production", s3_brand_bucket=None)
    assert settings.uses_local_brand_uploads is True


def test_uses_local_brand_uploads_false_when_s3_bucket_configured():
    settings = Settings(app_env="production", s3_brand_bucket="sailspipeline-brand-assets")
    assert settings.uses_local_brand_uploads is False

from app.agency_email_branding import (
    absolutize_email_html_asset_urls,
    contrast_text_color,
    render_email_brand_logo_img,
    render_email_cta_button,
    resolve_absolute_brand_asset_url,
)
from app.agency_email_branding import AgencyEmailBranding
from app.config import Settings


def test_contrast_text_color_returns_dark_on_light_background():
    assert contrast_text_color("#ffffff") == "#111111"
    assert contrast_text_color("#f0f0f0") == "#111111"


def test_contrast_text_color_returns_light_on_dark_background():
    assert contrast_text_color("#0d5c75") == "#ffffff"
    assert contrast_text_color("#102a43") == "#ffffff"


def test_render_email_cta_button_uses_primary_and_contrast_colors():
    html = render_email_cta_button(
        href="https://example.com/portal",
        label="Review & Sign",
        primary_color="#0d5c75",
        text_color="#ffffff",
    )

    assert 'href="https://example.com/portal"' in html
    assert "Review &amp; Sign" in html
    assert "background:#0d5c75" in html
    assert "color:#ffffff" in html


def test_resolve_absolute_brand_asset_url_prefixes_relative_upload_paths():
    absolute = resolve_absolute_brand_asset_url(
        "/static/uploads/logo_agency_demo.png",
        public_base_url="https://app.sailspipeline.com",
    )

    assert absolute == "https://app.sailspipeline.com/static/uploads/logo_agency_demo.png"


def test_resolve_absolute_brand_asset_url_normalizes_static_path_without_leading_slash():
    absolute = resolve_absolute_brand_asset_url(
        "static/uploads/logo_agency_demo.png",
        public_base_url="https://app.sailspipeline.com",
    )

    assert absolute == "https://app.sailspipeline.com/static/uploads/logo_agency_demo.png"


def test_resolve_absolute_brand_asset_url_rewrites_localhost_absolute_urls_to_production_base():
    absolute = resolve_absolute_brand_asset_url(
        "http://localhost:8080/static/uploads/logo_agency_demo.png",
        public_base_url="https://app.sailspipeline.com",
    )

    assert absolute == "https://app.sailspipeline.com/static/uploads/logo_agency_demo.png"


def test_resolve_absolute_brand_asset_url_preserves_external_cdn_urls():
    cdn_url = "https://cdn.example.com/brand-logos/logo.png"
    assert resolve_absolute_brand_asset_url(cdn_url, public_base_url="https://app.sailspipeline.com") == cdn_url


def test_render_email_brand_logo_img_uses_absolute_logo_url():
    branding = AgencyEmailBranding(
        agency_id="demo",
        agency_name="Cruise Sea-kers Travel",
        brand_logo_url="/static/uploads/logo_agency_demo.png",
        brand_logo_absolute_url="https://app.sailspipeline.com/static/uploads/logo_agency_demo.png",
        primary_color="#0d5c75",
        secondary_color="#17a2b8",
        primary_text_color="#ffffff",
        email_signature_block=None,
    )

    html = render_email_brand_logo_img(branding)

    assert 'src="https://app.sailspipeline.com/static/uploads/logo_agency_demo.png"' in html
    assert "Cruise Sea-kers Travel" in html


def test_absolutize_email_html_asset_urls_rewrites_signature_images(monkeypatch):
    import app.agency_email_branding as branding_module

    monkeypatch.setattr(
        branding_module,
        "settings",
        Settings(app_env="production"),
    )
    html = '<p>Best,<br/><img src="/static/uploads/signature_demo.png" alt="sig" /></p>'
    absolute = absolutize_email_html_asset_urls(html)

    assert 'src="https://app.sailspipeline.com/static/uploads/signature_demo.png"' in absolute


def test_settings_production_defaults_brand_asset_base_to_app_domain():
    settings = Settings(app_env="production", public_app_base_url="http://localhost:8080")

    assert settings.resolved_brand_asset_public_base_url == "https://app.sailspipeline.com"

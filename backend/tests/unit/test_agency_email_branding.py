from app.agency_email_branding import contrast_text_color, render_email_cta_button


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

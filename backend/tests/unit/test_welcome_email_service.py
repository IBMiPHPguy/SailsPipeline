from app.services.welcome_email_service import build_welcome_email_content


def test_welcome_email_includes_generated_username():
    html = build_welcome_email_content(
        admin_name="Jordan Lee",
        agency_name="Sunset Voyages",
        organization_handle="sunset-voyages",
        username="jordan.lee",
    )

    assert "jordan.lee" in html
    assert "firstname.lastname" in html
    assert "sunset-voyages" in html
    assert "Organization handle" in html
    assert "Username:" in html

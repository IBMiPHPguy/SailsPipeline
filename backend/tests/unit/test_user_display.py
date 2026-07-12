from app.user_display import (
    format_username_display_name,
    username_first_last,
    username_initials,
)


def test_format_username_display_name_from_dotted_username():
    assert format_username_display_name("robert.binetti") == "Robert Binetti"


def test_username_first_last_and_initials():
    assert username_first_last("robert.binetti") == ("Robert", "Binetti")
    assert username_initials("robert.binetti") == "RB"


def test_single_part_username():
    assert format_username_display_name("admin") == "Admin"
    assert username_first_last("admin") == ("Admin", "")
    assert username_initials("admin") == "AD"

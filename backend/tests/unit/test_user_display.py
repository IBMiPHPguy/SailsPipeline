import pytest

from app.user_display import format_username_display_name


@pytest.mark.unit
@pytest.mark.parametrize(
    ("username", "expected"),
    [
        ("robert.binetti", "Robert Binetti"),
        ("jane_doe", "Jane Doe"),
        ("alex", "Alex"),
        ("", ""),
    ],
)
def test_format_username_display_name(username: str, expected: str):
    assert format_username_display_name(username) == expected

from app.ui.dashboard import format_countdown


def test_countdown_shows_hours_minutes_and_seconds():
    assert format_countdown(3661) == "01:01:01"


def test_countdown_shows_days_when_over_24_hours():
    assert format_countdown(90061) == "1d 01:01:01"


def test_countdown_never_shows_negative_time():
    assert format_countdown(-10) == "00:00:00"


def test_countdown_handles_zero():
    assert format_countdown(0) == "00:00:00"

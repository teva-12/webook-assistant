import pytest

from app.browser.launcher import open_event_page


def test_opens_official_webook_url(monkeypatch):
    opened_urls = []

    def fake_open(url, new):
        opened_urls.append((url, new))
        return True

    monkeypatch.setattr("webbrowser.open", fake_open)

    result = open_event_page(
        "https://webook.com/en/events/test"
    )

    assert result is True
    assert opened_urls == [
        ("https://webook.com/en/events/test", 2)
    ]


@pytest.mark.parametrize(
    "url",
    [
        "http://webook.com/event",
        "https://example.com",
        "https://webook.com.evil.com/event",
        "javascript:alert(1)",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        open_event_page(url)
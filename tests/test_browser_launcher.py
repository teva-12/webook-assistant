from types import SimpleNamespace

import pytest

from app.browser import launcher


class FakePage:
    def __init__(self, url="about:blank"):
        self.url = url
        self.closed = False
        self.front = False
        self.navigations = []

    def is_closed(self):
        return self.closed

    def goto(self, url, **kwargs):
        self.url = url
        self.navigations.append((url, kwargs))

    def bring_to_front(self):
        self.front = True


class FakeContext:
    def __init__(self):
        self.pages = [FakePage()]
        self.closed = False

    def new_page(self):
        page = FakePage()
        self.pages.append(page)
        return page

    def close(self):
        self.closed = True


class FakePlaywright:
    def __init__(self):
        self.context = FakeContext()
        self.stopped = False
        self.chromium = SimpleNamespace(
            launch_persistent_context=lambda **kwargs: self._launch(kwargs)
        )
        self.launch_kwargs = None

    def _launch(self, kwargs):
        self.launch_kwargs = kwargs
        return self.context

    def stop(self):
        self.stopped = True


def reset_launcher():
    launcher._playwright = None
    launcher._context = None
    launcher._page = None


def test_opens_official_event_in_persistent_visible_browser(monkeypatch, tmp_path):
    reset_launcher()
    fake = FakePlaywright()
    monkeypatch.setattr(launcher, "sync_playwright", lambda: SimpleNamespace(start=lambda: fake))
    monkeypatch.setenv("WEBOOK_PROFILE_DIR", str(tmp_path / "profile"))

    result = launcher.open_event_page("https://webook.com/en/events/test")

    assert result is True
    assert fake.launch_kwargs["headless"] is False
    assert fake.launch_kwargs["user_data_dir"] == str(tmp_path / "profile")
    assert fake.context.pages[0].url == "https://webook.com/en/events/test"
    assert fake.context.pages[0].front is True

    # Reopening focuses/reuses the same page instead of starting another browser.
    assert launcher.open_event_page("https://webook.com/en/events/test") is True
    assert len(fake.context.pages) == 1

    launcher.close_browser()
    assert fake.context.closed is True
    assert fake.stopped is True
    reset_launcher()


@pytest.mark.parametrize(
    "url",
    [
        "http://webook.com/event",
        "https://example.com",
        "https://webook.com.evil.com/event",
        "https://user:pass@webook.com/event",
        "javascript:alert(1)",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        launcher.open_event_page(url)


def test_read_only_inspection_reads_visible_event_page(monkeypatch, tmp_path):
    reset_launcher()

    class FakeLocator:
        def inner_text(self, **kwargs):
            return "Bronze 405 Silver 865 Gold 1,150"

    class InspectablePage(FakePage):
        def title(self):
            return "Rashed Al Majid Concert"

        def locator(self, selector):
            assert selector == "body"
            return FakeLocator()

    fake = FakePlaywright()
    fake.context.pages[0] = InspectablePage("about:blank")
    monkeypatch.setattr(launcher, "sync_playwright", lambda: SimpleNamespace(start=lambda: fake))
    monkeypatch.setenv("WEBOOK_PROFILE_DIR", str(tmp_path / "profile"))

    assert launcher.open_event_page("https://webook.com/en/events/test") is True
    result = launcher.inspect_visible_event_page()

    assert result.page_title == "Rashed Al Majid Concert"
    assert [(item.name, item.price_sar) for item in result.categories] == [
        ("Bronze", 405),
        ("Silver", 865),
        ("Gold", 1150),
    ]
    assert fake.context.pages[0].navigations == [
        ("https://webook.com/en/events/test", {"wait_until": "domcontentloaded", "timeout": 60000})
    ]

    launcher.close_browser()
    reset_launcher()


def test_read_only_inspection_rejects_non_event_page(monkeypatch, tmp_path):
    reset_launcher()

    class FakeLocator:
        def inner_text(self, **kwargs):
            return "Private page"

    class InspectablePage(FakePage):
        def title(self):
            return "Account"

        def locator(self, selector):
            return FakeLocator()

    fake = FakePlaywright()
    fake.context.pages[0] = InspectablePage("about:blank")
    monkeypatch.setattr(launcher, "sync_playwright", lambda: SimpleNamespace(start=lambda: fake))
    monkeypatch.setenv("WEBOOK_PROFILE_DIR", str(tmp_path / "profile"))

    assert launcher.open_event_page("https://webook.com/en/events/test") is True
    fake.context.pages[0].url = "https://webook.com/en/subscriptions"

    with pytest.raises(RuntimeError, match="limited to the visible Webook event page"):
        launcher.inspect_visible_event_page()

    launcher.close_browser()
    reset_launcher()


def test_inspection_expands_exact_ticket_types_disclosure_and_waits_for_silver(
    monkeypatch, tmp_path
):
    reset_launcher()

    class DynamicBody:
        def __init__(self, state):
            self.state = state

        def inner_text(self, **kwargs):
            return self.state["text"]

    class Disclosure:
        def __init__(self, state):
            self.state = state
            self.clicked = False

        def count(self):
            return 1

        def is_visible(self):
            return True

        def inner_text(self, **kwargs):
            return "See more (6)"

        def click(self, **kwargs):
            self.clicked = True
            self.state["text"] = (
                "Ticket types\nRoyal 3,450\nDiamond 2,875\nPlatinum 2,300\n"
                "Gold 1,150\nSilver 865\nBronze 405"
            )

    class ExpandablePage(FakePage):
        def __init__(self, url="about:blank"):
            super().__init__(url)
            self.state = {
                "text": "Ticket types\nRoyal 3,450\nDiamond 2,875\n"
                "Platinum 2,300\nSee more (6)"
            }
            self.body = DynamicBody(self.state)
            self.disclosure = Disclosure(self.state)

        def title(self):
            return "Rashed Al Majid Concert"

        def locator(self, selector):
            assert selector == "body"
            return self.body

        def get_by_text(self, pattern):
            assert pattern.pattern.startswith("^")
            return self.disclosure

        def wait_for_timeout(self, milliseconds):
            pass

    fake = FakePlaywright()
    fake.context.pages[0] = ExpandablePage("about:blank")
    monkeypatch.setattr(
        launcher, "sync_playwright", lambda: SimpleNamespace(start=lambda: fake)
    )
    monkeypatch.setenv("WEBOOK_PROFILE_DIR", str(tmp_path / "profile"))

    assert launcher.open_event_page("https://webook.com/en/events/test") is True
    result = launcher.inspect_visible_event_page()

    assert fake.context.pages[0].disclosure.clicked is True
    assert result.ticket_types_expanded is True
    assert [(item.name, item.price_sar) for item in result.categories] == [
        ("Bronze", 405),
        ("Silver", 865),
        ("Gold", 1150),
        ("Platinum", 2300),
        ("Diamond", 2875),
        ("Royal", 3450),
    ]

    launcher.close_browser()
    reset_launcher()


def test_inspection_does_not_click_generic_see_more_controls(monkeypatch, tmp_path):
    reset_launcher()

    class Body:
        def inner_text(self, **kwargs):
            return "Royal 3,450\nDiamond 2,875\nPlatinum 2,300\nSee more"

    class AmbiguousDisclosure:
        def count(self):
            return 0

    class PageWithoutExactDisclosure(FakePage):
        def title(self):
            return "Rashed Al Majid Concert"

        def locator(self, selector):
            return Body()

        def get_by_text(self, pattern):
            return AmbiguousDisclosure()

    fake = FakePlaywright()
    fake.context.pages[0] = PageWithoutExactDisclosure("about:blank")
    monkeypatch.setattr(
        launcher, "sync_playwright", lambda: SimpleNamespace(start=lambda: fake)
    )
    monkeypatch.setenv("WEBOOK_PROFILE_DIR", str(tmp_path / "profile"))

    assert launcher.open_event_page("https://webook.com/en/events/test") is True
    result = launcher.inspect_visible_event_page()

    assert result.ticket_types_expanded is False
    assert [item.name for item in result.categories] == [
        "Platinum", "Diamond", "Royal"
    ]

    launcher.close_browser()
    reset_launcher()



def test_expands_first_numbered_ticket_disclosure_when_page_has_multiple_counts(
    monkeypatch, tmp_path
):
    reset_launcher()

    class DynamicBody:
        def __init__(self, state):
            self.state = state

        def inner_text(self, **kwargs):
            return self.state["text"]

    class Disclosure:
        def __init__(self, state, label):
            self.state = state
            self.label = label
            self.clicked = False

        def is_visible(self):
            return True

        def inner_text(self, **kwargs):
            return self.label

        def click(self, **kwargs):
            self.clicked = True
            self.state["text"] = (
                "Bronze ticket €70.26\nSilver ticket €94.07\nGold ticket €130.99\n"
                "Platinum ticket €154.00\nSee more (8)"
            )

    class DisclosureCollection:
        def __init__(self, items):
            self.items = items

        def count(self):
            return len(self.items)

        def nth(self, index):
            return self.items[index]

    class ExpandablePage(FakePage):
        def __init__(self, url="about:blank"):
            super().__init__(url)
            self.state = {"text": "Bronze ticket €70.26\nSilver ticket €94.07\nGold ticket €130.99\nSee more (5)\nSee more (8)"}
            self.body = DynamicBody(self.state)
            self.ticket_disclosure = Disclosure(self.state, "See more (5)")
            self.terms_disclosure = Disclosure(self.state, "See more (8)")

        def title(self):
            return "Aseel Hameem at Vocally Riyadh"

        def locator(self, selector):
            assert selector == "body"
            return self.body

        def get_by_text(self, pattern):
            assert "\\d+" in pattern.pattern
            return DisclosureCollection([self.ticket_disclosure, self.terms_disclosure])

        def wait_for_timeout(self, milliseconds):
            pass

    fake = FakePlaywright()
    fake.context.pages[0] = ExpandablePage("about:blank")
    monkeypatch.setattr(
        launcher, "sync_playwright", lambda: SimpleNamespace(start=lambda: fake)
    )
    monkeypatch.setenv("WEBOOK_PROFILE_DIR", str(tmp_path / "profile"))

    assert launcher.open_event_page("https://webook.com/en/sa/ruh/music-events/events/test") is True
    result = launcher.inspect_visible_event_page()

    assert fake.context.pages[0].ticket_disclosure.clicked is True
    assert fake.context.pages[0].terms_disclosure.clicked is False
    assert result.ticket_types_expand_clicked is True
    assert result.ticket_types_expanded is True
    assert [(item.name, item.price_display) for item in result.categories] == [
        ("Bronze", "€70.26"),
        ("Silver", "€94.07"),
        ("Gold", "€130.99"),
        ("Platinum", "€154.00"),
    ]

    launcher.close_browser()
    reset_launcher()

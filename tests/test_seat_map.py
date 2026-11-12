from app.booking.seat_map import _visible_tooltip_text


class _TextLocator:
    def __init__(self, value):
        self.value = value

    def count(self):
        return 1 if self.value else 0

    def nth(self, index):
        return self

    def inner_text(self, timeout=None):
        return self.value


class _Page:
    def locator(self, selector):
        if selector == '[role="tooltip"]:visible':
            return _TextLocator("Bronze · Row A · Seat 12")
        return _TextLocator("")


def test_reads_only_visible_tooltip_text():
    assert _visible_tooltip_text(_Page()) == "Bronze · Row A · Seat 12"

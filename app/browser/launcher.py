"""Launch and inspect a visible, persistent Webook browser session.

The user signs in manually. The only automated page interaction in the event
inspection flow is expanding the first numbered public ticket-type disclosure.
The app never clicks Book, enters a queue, selects seats, submits forms, or pays.
"""

import os
import re
from pathlib import Path
from time import monotonic
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from app.monitoring.page_inspector import (
    build_page_inspection,
    extract_visible_categories,
)


_ALLOWED_HOSTS = {"webook.com", "www.webook.com"}
_playwright = None
_context = None
_page = None
_EXPAND_TICKET_TYPES = re.compile(r"^\s*See more\s*\(\s*\d+\s*\)\s*$", re.IGNORECASE)


def validate_event_url(url: str) -> None:
    parsed_url = urlparse(url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in _ALLOWED_HOSTS
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.port not in (None, 443)
    ):
        raise ValueError("Only official Webook HTTPS URLs are allowed.")


def _profile_directory() -> Path:
    configured = os.getenv("WEBOOK_PROFILE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / ".local" / "share"
    return base / "WebookAssistant" / "browser-profile"


def open_event_page(url: str) -> bool:
    """Open the official event in a visible browser with a persistent profile.

    The persistent profile may retain the user's own Webook login session on
    this computer. The app itself never handles or exports the login data.
    """
    global _playwright, _context, _page

    validate_event_url(url)

    try:
        if _context is None:
            profile_dir = _profile_directory()
            profile_dir.mkdir(parents=True, exist_ok=True)
            _playwright = sync_playwright().start()
            _context = _playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                viewport=None,
                args=["--start-maximized"],
            )

        if _page is None or _page.is_closed():
            _page = _context.pages[0] if _context.pages else _context.new_page()

        if _page.url != url:
            _page.goto(url, wait_until="domcontentloaded", timeout=60000)
        _page.bring_to_front()
        return True

    except PlaywrightError:
        try:
            if _context is not None:
                _context.close()
        except PlaywrightError:
            pass
        _context = None
        _page = None
        if _playwright is not None:
            _playwright.stop()
        _playwright = None
        return False


def _expand_ticket_types_if_collapsed(page) -> tuple[bool, bool]:
    """Expand the first numbered public disclosure on the event page.

    Webook event pages use different counts (for example, See more (5) or
    See more (6)). The first numbered disclosure appears in the ticket-types
    section; later numbered disclosures may belong to terms/details. Only the
    first one is clicked. Generic "See more" controls are never clicked.
    """
    body = page.locator("body")
    current_text = body.inner_text(timeout=5000)
    current_categories = {item.name for item in extract_visible_categories(current_text)}

    if not hasattr(page, "get_by_text"):
        return False, {"Bronze", "Silver"}.issubset(current_categories)

    disclosures = page.get_by_text(_EXPAND_TICKET_TYPES)
    matches = disclosures.count()
    if matches == 0:
        return False, {"Bronze", "Silver"}.issubset(current_categories)

    # The first numbered disclosure is the ticket-types disclosure on the
    # supported Webook event-page layout. Do not click subsequent disclosures.
    disclosure = disclosures.nth(0) if matches > 1 else disclosures
    if not disclosure.is_visible():
        return False, {"Bronze", "Silver"}.issubset(current_categories)

    label = disclosure.inner_text(timeout=3000).strip()
    disclosure.click(timeout=5000)

    deadline = monotonic() + 6.0
    while monotonic() < deadline:
        updated_text = body.inner_text(timeout=5000)
        updated_categories = {
            item.name for item in extract_visible_categories(updated_text)
        }
        disclosure_collapsed_label_gone = label not in updated_text
        if (
            updated_text != current_text
            and (
                len(updated_categories) > len(current_categories)
                or disclosure_collapsed_label_gone
            )
        ):
            return True, True
        page.wait_for_timeout(250)

    return True, False


def inspect_visible_event_page():
    """Read the event page and expand its ticket-type disclosure if needed.

    The app may click the first numbered "See more (N)" ticket disclosure to reveal
    additional categories. It does not click Book, enter a queue, select seats, submit a
    form, reload the page, or access cookies/storage/network APIs.
    """
    if _page is None or _page.is_closed():
        raise RuntimeError("Open the official event page first (menu option 5).")

    validate_event_url(_page.url)
    parsed_url = urlparse(_page.url)
    if "/events/" not in parsed_url.path.lower():
        raise RuntimeError(
            "Inspection is limited to the visible Webook event page. "
            "Return to the event page manually in the browser first."
        )

    try:
        expansion_clicked, expanded = _expand_ticket_types_if_collapsed(_page)
        page_title = _page.title()
        visible_text = _page.locator("body").inner_text(timeout=5000)
    except PlaywrightError as error:
        raise RuntimeError(
            "Could not inspect the currently visible event page. "
            "No booking or queue action was taken."
        ) from error

    return build_page_inspection(
        page_title,
        _page.url,
        visible_text,
        ticket_types_expand_clicked=expansion_clicked,
        ticket_types_expanded=expanded,
    )


def close_browser() -> None:
    """Close the persistent browser cleanly when the user ends the session."""
    global _playwright, _context, _page

    try:
        if _context is not None:
            _context.close()
    except PlaywrightError:
        # The user may have closed Chromium manually. Treat that as a clean shutdown.
        pass
    finally:
        _context = None
        _page = None
        if _playwright is not None:
            try:
                _playwright.stop()
            except PlaywrightError:
                pass
        _playwright = None


def scan_visible_seat_map():
    """Hover-scan visible seat-map tooltips without selecting any seats."""
    if _page is None or _page.is_closed():
        raise RuntimeError("افتح صفحة اختيار المقاعد أولاً من المتصفح.")
    validate_event_url(_page.url)
    from app.booking.seat_map import scan_visible_seat_tooltips
    return scan_visible_seat_tooltips(_page)


def capture_seat_map_screenshot(output_path: str):
    """Capture only the visible seat-map canvas for the user's review."""
    if _page is None or _page.is_closed():
        raise RuntimeError("افتح صفحة اختيار المقاعد أولاً من المتصفح.")
    validate_event_url(_page.url)
    from app.booking.seat_map import capture_visible_seat_map
    return capture_visible_seat_map(_page, output_path)

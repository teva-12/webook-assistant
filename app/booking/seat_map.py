"""Read-only discovery of seat labels rendered by visible hover tooltips.

No hidden app state, network traffic, cookies, local storage, canvas internals,
seat clicks, selection, checkout, or payment are used.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HoverObservation:
    x: float
    y: float
    text: str


@dataclass(frozen=True)
class VisibleSeat:
    row: str
    number: int
    status: str
    category: str | None
    source_text: str


@dataclass(frozen=True)
class AdjacentSeatPair:
    first: VisibleSeat
    second: VisibleSeat


_ROW = re.compile(r"\brow\s*[:#-]?\s*([a-z0-9]+)\b", re.I)

_SEAT = re.compile(
    r"\b(?:seat|chair)\s*(?:no\.?|number|#|:)?\s*(\d+)\b",
    re.I,
)
_AVAILABLE = re.compile(r"\b(available|free|open seat)\b", re.I)
_UNAVAILABLE = re.compile(r"\b(sold|reserved|unavailable|not available|occupied|blocked)\b", re.I)
_CATEGORY = re.compile(r"\b(bronze|silver|gold|platinum|diamond|royal)\b", re.I)


def parse_visible_seat_tooltip(text: str) -> VisibleSeat | None:
    """Return a seat only if row, number and explicit availability are visible."""
    if not text or _UNAVAILABLE.search(text) or not _AVAILABLE.search(text):
        return None
    row_match = _ROW.search(text)
    seat_match = _SEAT.search(text)
    if not row_match or not seat_match:
        return None
    category_match = _CATEGORY.search(text)
    return VisibleSeat(
        row=row_match.group(1).upper(),
        number=int(seat_match.group(1)),
        status="available",
        category=category_match.group(1).title() if category_match else None,
        source_text=text.strip(),
    )


def find_adjacent_visible_pairs(
    observations: Iterable[HoverObservation], *, category: str = "Bronze"
) -> list[AdjacentSeatPair]:
    """Find consecutive labels in one row and one category.

    Consecutive numbering is only a candidate for adjacency. A seat map may
    contain aisles or numbering gaps, so the user must visually confirm it.
    """
    seats: dict[tuple[str, int, str], VisibleSeat] = {}
    for observation in observations:
        seat = parse_visible_seat_tooltip(observation.text)
        if seat is None or seat.category is None:
            continue
        if category and seat.category.casefold() != category.casefold():
            continue
        seats[(seat.row, seat.number, seat.category)] = seat

    pairs: list[AdjacentSeatPair] = []
    for (row, number, cat), seat in sorted(seats.items()):
        following = seats.get((row, number + 1, cat))
        if following:
            pairs.append(AdjacentSeatPair(seat, following))
    return pairs


def _visible_canvas(page):
    canvases = page.locator("canvas:visible")
    candidates = []
    for index in range(canvases.count()):
        canvas = canvases.nth(index)
        box = canvas.bounding_box()
        if box and box["width"] >= 250 and box["height"] >= 250:
            candidates.append((box["width"] * box["height"], box))
    if not candidates:
        raise RuntimeError("لم أجد خريطة مقاعد Canvas ظاهرة.")
    return max(candidates, key=lambda item: item[0])[1]


def _visible_tooltip_text(page) -> str:
    selectors = (
        '[role="tooltip"]:visible',
        '[aria-live="polite"]:visible',
        '[aria-live="assertive"]:visible',
        '.tooltip:visible',
        '.seat-tooltip:visible',
    )
    chunks = []
    for selector in selectors:
        locator = page.locator(selector)
        try:
            for index in range(min(locator.count(), 8)):
                value = locator.nth(index).inner_text(timeout=500).strip()
                if value:
                    chunks.append(value)
        except Exception:
            continue
    return re.sub(r"\s+", " ", " | ".join(dict.fromkeys(chunks))).strip()


def scan_visible_seat_tooltips(page, *, max_points: int = 240) -> list[HoverObservation]:
    """Hover a coarse grid and collect only explicitly visible tooltip text."""
    if not 20 <= max_points <= 600:
        raise ValueError("max_points must be between 20 and 600")
    box = _visible_canvas(page)
    cols = max(4, int((max_points / 2) ** 0.5))
    rows = max(4, (max_points + cols - 1) // cols)
    found: dict[str, HoverObservation] = {}
    for row in range(rows):
        for col in range(cols):
            if len(found) >= max_points:
                break
            x = box["x"] + box["width"] * (0.06 + 0.88 * col / max(1, cols - 1))
            y = box["y"] + box["height"] * (0.06 + 0.88 * row / max(1, rows - 1))
            page.mouse.move(x, y)
            page.wait_for_timeout(140)
            tooltip = _visible_tooltip_text(page)
            if tooltip and len(tooltip) <= 300:
                found.setdefault(tooltip, HoverObservation(x, y, tooltip))
        if len(found) >= max_points:
            break
    page.mouse.move(box["x"] + 4, box["y"] + 4)
    return list(found.values())

def capture_visible_seat_map(page, output_path: str) -> str:
    """Save a screenshot of the largest visible seat-map canvas."""
    canvases = page.locator("canvas:visible")
    candidates = []

    for index in range(canvases.count()):
        canvas = canvases.nth(index)
        box = canvas.bounding_box()

        if box and box["width"] >= 250 and box["height"] >= 250:
            area = box["width"] * box["height"]
            candidates.append((area, canvas))

    if not candidates:
        raise RuntimeError("لم أجد خريطة مقاعد Canvas ظاهرة.")

    _, selected_canvas = max(candidates, key=lambda item: item[0])

    selected_canvas.screenshot(path=output_path)
    return output_path

"""Visible, hover-only discovery for Webook's canvas seat map.

This module deliberately does not inspect hidden application state, network traffic,
local storage, cookies, or chart internals. It uses only the visible canvas and
text rendered to the page after a normal pointer hover.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError


@dataclass(frozen=True)
class HoverObservation:
    x: float
    y: float
    text: str


def _visible_canvas(page):
    canvases = page.locator("canvas:visible")
    if canvases.count() == 0:
        raise RuntimeError("لم أجد خريطة مقاعد Canvas ظاهرة. افتح خطوة اختيار المقاعد أولاً.")
    # Webook's seat chart is the large visible canvas, not tiny decorative canvases.
    candidates = []
    for index in range(canvases.count()):
        item = canvases.nth(index)
        box = item.bounding_box()
        if box and box["width"] >= 250 and box["height"] >= 250:
            candidates.append((box["width"] * box["height"], item, box))
    if not candidates:
        raise RuntimeError("وجدت Canvas، لكن لم أجد خريطة كبيرة مناسبة للفحص.")
    _, canvas, box = max(candidates, key=lambda row: row[0])
    return canvas, box


def scan_visible_seat_tooltips(page, *, max_points: int = 240) -> list[HoverObservation]:
    """Hover a sparse grid over the visible chart and collect newly rendered text.

    Hover only: no seat is clicked or selected. This is a first-pass map calibration
    because tooltip wording and chart geometry vary by event.
    """
    if max_points < 20 or max_points > 600:
        raise ValueError("max_points must be between 20 and 600")
    canvas, box = _visible_canvas(page)
    before = page.locator("body").inner_text(timeout=5000)
    # Stay away from the canvas border and sample a coarse grid to avoid excessive
    # pointer activity. The user can zoom into the desired layer before scanning.
    cols = max(4, int((max_points / 2) ** 0.5))
    rows = max(4, (max_points + cols - 1) // cols)
    observations: dict[str, HoverObservation] = {}
    for row in range(rows):
        for col in range(cols):
            if len(observations) >= max_points:
                break
            x = box["x"] + box["width"] * (0.06 + 0.88 * (col / max(1, cols - 1)))
            y = box["y"] + box["height"] * (0.06 + 0.88 * (row / max(1, rows - 1)))
            page.mouse.move(x, y)
            page.wait_for_timeout(90)
            current = page.locator("body").inner_text(timeout=3000)
            delta = current.replace(before, "").strip()
            # Some sites replace a tooltip in-place, so also capture compact text
            # near the end when the complete body string did not grow.
            if not delta and current != before:
                delta = current[-500:].strip()
            delta = re.sub(r"\s+", " ", delta)
            if delta and len(delta) <= 240 and delta not in {"Loading", "Loading..."}:
                observations.setdefault(delta, HoverObservation(x=x, y=y, text=delta))
        if len(observations) >= max_points:
            break
    page.mouse.move(box["x"] + 4, box["y"] + 4)
    return list(observations.values())

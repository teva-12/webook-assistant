"""Read-only extraction from text already rendered on the official event page.

This module does not infer ticket availability, queue position, or seat adjacency.
It only reports category/price pairs that are explicitly visible in page text.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
import re


CATEGORIES = ("Bronze", "Silver", "Gold", "Platinum", "Diamond", "Royal")
_CURRENCY_PATTERN = r"(?P<currency>SAR|USD|EUR|GBP|AED|EGP|€|£|\$|ر\.س)?"
_AMOUNT_PATTERN = r"(?P<amount>\d[\d,]*(?:\.\d{1,2})?)"


@dataclass(frozen=True)
class VisibleCategory:
    name: str
    price_sar: int | None
    price_display: str
    currency: str | None = None


@dataclass(frozen=True)
class PageInspection:
    page_title: str
    page_url: str
    inspected_at: str
    categories: tuple[VisibleCategory, ...]
    availability_evidence: tuple[str, ...]
    ticket_types_expand_clicked: bool = False
    ticket_types_expanded: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["categories"] = [asdict(item) for item in self.categories]
        return data


def _currency_code(token: str | None) -> str | None:
    if not token:
        return None
    normalized = token.upper()
    return {
        "€": "EUR",
        "£": "GBP",
        "$": "USD",
        "ر.س": "SAR",
    }.get(token, normalized)


def _price_display(token: str | None, amount: str) -> str:
    if token in {"€", "£", "$"}:
        return f"{token}{amount}"
    if token:
        return f"{token} {amount}"
    return amount


def extract_visible_categories(page_text: str) -> tuple[VisibleCategory, ...]:
    """Extract visible category/price pairs, preserving the displayed currency."""
    found: list[VisibleCategory] = []
    for name in CATEGORIES:
        pattern = (
            rf"\b{re.escape(name)}\b(?:\s+ticket)?\s*"
            rf"{_CURRENCY_PATTERN}\s*{_AMOUNT_PATTERN}\b"
        )
        match = re.search(pattern, page_text, flags=re.IGNORECASE)
        if not match:
            continue

        token = match.group("currency")
        amount = match.group("amount")
        currency = _currency_code(token)
        price_sar = None
        if (currency in {None, "SAR"}) and "." not in amount:
            # Keep the legacy integer field for SAR/integer pages; do not
            # convert or relabel foreign-currency values as SAR.
            price_sar = int(amount.replace(",", ""))

        found.append(
            VisibleCategory(
                name=name,
                price_sar=price_sar,
                price_display=_price_display(token, amount),
                currency=currency,
            )
        )
    return tuple(found)


def extract_explicit_availability_evidence(page_text: str) -> tuple[str, ...]:
    """Return short explicit phrases; never convert absence of text into a status."""
    phrases = (
        "sold out",
        "currently unavailable",
        "tickets available",
        "limited tickets available",
        "not available",
    )
    lowered = " ".join(page_text.lower().split())
    evidence = []
    for phrase in phrases:
        if phrase in lowered:
            evidence.append(phrase)
    return tuple(evidence)


def build_page_inspection(
    page_title: str,
    page_url: str,
    page_text: str,
    ticket_types_expand_clicked: bool = False,
    ticket_types_expanded: bool = False,
) -> PageInspection:
    return PageInspection(
        page_title=page_title.strip(),
        page_url=page_url,
        inspected_at=datetime.now().astimezone().isoformat(),
        categories=extract_visible_categories(page_text),
        availability_evidence=extract_explicit_availability_evidence(page_text),
        ticket_types_expand_clicked=ticket_types_expand_clicked,
        ticket_types_expanded=ticket_types_expanded,
    )

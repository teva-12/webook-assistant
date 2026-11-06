from dataclasses import dataclass

from app.core.models import TicketCategory


@dataclass(frozen=True)
class CategoryDecision:
    category: TicketCategory | None
    requires_approval: bool
    reason: str


def choose_category(
    bronze_available: bool,
    silver_available: bool,
) -> CategoryDecision:

    if bronze_available:
        return CategoryDecision(
            category=TicketCategory.BRONZE,
            requires_approval=False,
            reason="Preferred category is available.",
        )

    if silver_available:
        return CategoryDecision(
            category=TicketCategory.SILVER,
            requires_approval=True,
            reason="Bronze unavailable. Silver requires user approval.",
        )

    return CategoryDecision(
        category=None,
        requires_approval=False,
        reason="No preferred or fallback category is available.",
    )
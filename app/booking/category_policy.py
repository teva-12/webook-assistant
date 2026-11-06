from dataclasses import dataclass

from app.core.models import TicketCategory, BookingPreferences


@dataclass(frozen=True)
class CategoryAvailability:
    available_tickets: int
    adjacent_seats_available: bool


@dataclass(frozen=True)
class CategoryDecision:
    category: TicketCategory | None
    requires_approval: bool
    reason: str


def _meets_preferences(
    availability: CategoryAvailability,
    preferences: BookingPreferences,
) -> bool:
    if availability.available_tickets < preferences.quantity:
        return False

    if (
        preferences.require_adjacent_seats
        and not availability.adjacent_seats_available
    ):
        return False

    return True


def choose_category(
    bronze: CategoryAvailability,
    silver: CategoryAvailability,
    preferences: BookingPreferences | None = None,
) -> CategoryDecision:
    preferences = preferences or BookingPreferences()

    if _meets_preferences(bronze, preferences):
        return CategoryDecision(
            category=TicketCategory.BRONZE,
            requires_approval=False,
            reason="Bronze meets the requested quantity and seating preferences.",
        )

    if _meets_preferences(silver, preferences):
        return CategoryDecision(
            category=TicketCategory.SILVER,
            requires_approval=preferences.fallback_requires_approval,
            reason="Bronze does not meet the preferences. Silver is an alternative.",
        )

    return CategoryDecision(
        category=None,
        requires_approval=False,
        reason="No category meets the requested quantity and seating preferences.",
    )
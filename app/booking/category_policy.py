from dataclasses import dataclass

from app.core.models import TicketCategory, BookingPreferences


@dataclass(frozen=True)
class CategoryAvailability:
    available_tickets: int
    adjacent_seats_available: bool = False


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

    if preferences.quantity > 1 and preferences.require_adjacent_seats:
        return availability.adjacent_seats_available

    return True


def choose_category(
    bronze: CategoryAvailability | None = None,
    silver: CategoryAvailability | None = None,
    preferences: BookingPreferences | None = None,
    *,
    availability_by_category: dict[TicketCategory, CategoryAvailability] | None = None,
) -> CategoryDecision:
    """Choose the preferred category, then the approved fallback.

    The legacy bronze/silver arguments remain supported for existing callers.
    Availability is always supplied from explicit user observation, never guessed.
    """
    preferences = preferences or BookingPreferences()
    available = availability_by_category or {
        TicketCategory.BRONZE: bronze or CategoryAvailability(0),
        TicketCategory.SILVER: silver or CategoryAvailability(0),
    }

    preferred = available.get(preferences.preferred_category, CategoryAvailability(0))
    if _meets_preferences(preferred, preferences):
        return CategoryDecision(
            category=preferences.preferred_category,
            requires_approval=False,
            reason=(
                f"{preferences.preferred_category.value.title()} meets the requested "
                f"quantity ({preferences.quantity}) and seating preferences."
            ),
        )

    fallback = available.get(preferences.fallback_category, CategoryAvailability(0))
    if preferences.fallback_category != preferences.preferred_category and _meets_preferences(
        fallback, preferences
    ):
        return CategoryDecision(
            category=preferences.fallback_category,
            requires_approval=preferences.fallback_requires_approval,
            reason=(
                f"{preferences.preferred_category.value.title()} does not meet the "
                f"preferences. {preferences.fallback_category.value.title()} is an alternative."
            ),
        )

    return CategoryDecision(
        category=None,
        requires_approval=False,
        reason=(
            f"No selected category meets the request for {preferences.quantity} "
            "ticket(s) and the chosen seating condition."
        ),
    )

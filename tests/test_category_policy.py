from app.booking.category_policy import (
    CategoryAvailability,
    choose_category,
)
from app.core.models import BookingPreferences, TicketCategory


def test_bronze_selected_when_two_adjacent_tickets_available():
    decision = choose_category(
        bronze=CategoryAvailability(2, True),
        silver=CategoryAvailability(2, True),
    )

    assert decision.category == TicketCategory.BRONZE
    assert decision.requires_approval is False


def test_silver_requires_approval_when_bronze_does_not_meet_preferences():
    decision = choose_category(
        bronze=CategoryAvailability(2, False),
        silver=CategoryAvailability(2, True),
    )

    assert decision.category == TicketCategory.SILVER
    assert decision.requires_approval is True


def test_no_category_when_less_than_two_tickets_available():
    decision = choose_category(
        bronze=CategoryAvailability(1, True),
        silver=CategoryAvailability(1, True),
    )

    assert decision.category is None


def test_no_category_when_no_adjacent_seats_available():
    decision = choose_category(
        bronze=CategoryAvailability(2, False),
        silver=CategoryAvailability(2, False),
    )

    assert decision.category is None


def test_quantity_can_be_customized():
    preferences = BookingPreferences(quantity=1)

    decision = choose_category(
        bronze=CategoryAvailability(1, True),
        silver=CategoryAvailability(2, True),
        preferences=preferences,
    )

    assert decision.category == TicketCategory.BRONZE


def test_silver_does_not_require_approval_when_preference_disabled():
    preferences = BookingPreferences(fallback_requires_approval=False)

    decision = choose_category(
        bronze=CategoryAvailability(0, False),
        silver=CategoryAvailability(2, True),
        preferences=preferences,
    )

    assert decision.category == TicketCategory.SILVER
    assert decision.requires_approval is False

from app.booking.category_policy import CategoryAvailability, choose_category
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


def test_quantity_one_does_not_require_adjacency():
    preferences = BookingPreferences(quantity=1)
    decision = choose_category(
        preferences=preferences,
        availability_by_category={
            TicketCategory.BRONZE: CategoryAvailability(1, False),
            TicketCategory.SILVER: CategoryAvailability(1, False),
        },
    )
    assert decision.category == TicketCategory.BRONZE


def test_quantity_three_requires_three_adjacent_when_requested():
    preferences = BookingPreferences(quantity=3)
    decision = choose_category(
        preferences=preferences,
        availability_by_category={
            TicketCategory.BRONZE: CategoryAvailability(3, False),
            TicketCategory.SILVER: CategoryAvailability(3, True),
        },
    )
    assert decision.category == TicketCategory.SILVER
    assert decision.requires_approval is True


def test_user_can_choose_any_visible_category_as_preference():
    preferences = BookingPreferences(
        quantity=2,
        preferred_category=TicketCategory.GOLD,
        fallback_category=TicketCategory.SILVER,
    )
    decision = choose_category(
        preferences=preferences,
        availability_by_category={
            TicketCategory.GOLD: CategoryAvailability(2, True),
            TicketCategory.SILVER: CategoryAvailability(2, True),
        },
    )
    assert decision.category == TicketCategory.GOLD


def test_silver_does_not_require_approval_when_preference_disabled():
    preferences = BookingPreferences(fallback_requires_approval=False)
    decision = choose_category(
        preferences=preferences,
        availability_by_category={
            TicketCategory.BRONZE: CategoryAvailability(0, False),
            TicketCategory.SILVER: CategoryAvailability(2, True),
        },
    )
    assert decision.category == TicketCategory.SILVER
    assert decision.requires_approval is False

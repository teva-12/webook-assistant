
import pytest

from app.core.models import BookingStage
from app.monitoring.stage_transitions import (
    ALLOWED_TRANSITIONS,
    InvalidTransitionError,
    is_transition_allowed,
    validate_transition,
)


ACTIVE_STAGES = [
    BookingStage.READY,
    BookingStage.WAITING_FOR_USER,
    BookingStage.TICKET_SELECTION,
]

TERMINAL_STAGES = [
    BookingStage.CHECKOUT,
    BookingStage.COMPLETED,
    BookingStage.STOPPED,
]


@pytest.mark.parametrize("stage", list(ALLOWED_TRANSITIONS))
def test_same_stage_is_never_allowed(stage):
    assert is_transition_allowed(stage, stage) is False


@pytest.mark.parametrize("stage", list(ALLOWED_TRANSITIONS))
def test_same_stage_raises_clear_error(stage):
    with pytest.raises(InvalidTransitionError, match="Already in stage"):
        validate_transition(stage, stage)


@pytest.mark.parametrize(
    "current, target",
    [
        (BookingStage.READY, BookingStage.WAITING_FOR_USER),
        (BookingStage.READY, BookingStage.TICKET_SELECTION),
        (BookingStage.WAITING_FOR_USER, BookingStage.TICKET_SELECTION),
        (BookingStage.TICKET_SELECTION, BookingStage.WAITING_FOR_USER),
        (BookingStage.TICKET_SELECTION, BookingStage.READY),
    ],
)
def test_valid_transitions_are_allowed(current, target):
    assert is_transition_allowed(current, target) is True
    validate_transition(current, target)


@pytest.mark.parametrize("stage", ACTIVE_STAGES)
def test_every_active_stage_can_reach_checkout(stage):
    assert is_transition_allowed(stage, BookingStage.CHECKOUT) is True


@pytest.mark.parametrize("current", TERMINAL_STAGES)
@pytest.mark.parametrize("target", list(BookingStage))
def test_terminal_stages_allow_no_transitions(current, target):
    assert is_transition_allowed(current, target) is False


@pytest.mark.parametrize("target", ACTIVE_STAGES)
def test_cannot_leave_checkout(target):
    with pytest.raises(InvalidTransitionError, match="not allowed"):
        validate_transition(BookingStage.CHECKOUT, target)

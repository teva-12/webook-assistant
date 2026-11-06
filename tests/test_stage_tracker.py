
import pytest

from app.core.models import BookingStage
from app.monitoring.stage_tracker import StageTracker
from app.monitoring.stage_transitions import InvalidTransitionError


def test_current_stage_property_follows_transitions():
    tracker = StageTracker()
    assert tracker.current_stage is None

    tracker.start(BookingStage.READY)
    assert tracker.current_stage == BookingStage.READY

    tracker.transition(BookingStage.TICKET_SELECTION)
    assert tracker.current_stage == BookingStage.TICKET_SELECTION

    tracker.stop()
    assert tracker.current_stage is None


def test_transition_to_current_stage_raises():
    tracker = StageTracker()
    tracker.start(BookingStage.READY)

    with pytest.raises(InvalidTransitionError):
        tracker.transition(BookingStage.READY)


def test_duplicate_transition_creates_no_record():
    tracker = StageTracker()
    tracker.start(BookingStage.READY)

    with pytest.raises(InvalidTransitionError):
        tracker.transition(BookingStage.READY)

    assert len(tracker.records) == 0
    assert tracker.current_stage == BookingStage.READY


def test_duplicate_after_valid_transition_keeps_one_record():
    tracker = StageTracker()
    tracker.start(BookingStage.READY)
    tracker.transition(BookingStage.WAITING_FOR_USER)

    with pytest.raises(InvalidTransitionError):
        tracker.transition(BookingStage.WAITING_FOR_USER)

    assert len(tracker.records) == 1
    assert tracker.records[0].stage == BookingStage.READY
    assert tracker.current_stage == BookingStage.WAITING_FOR_USER


def test_valid_transition_after_rejected_one_still_works():
    tracker = StageTracker()
    tracker.start(BookingStage.READY)

    with pytest.raises(InvalidTransitionError):
        tracker.transition(BookingStage.READY)

    record = tracker.transition(BookingStage.TICKET_SELECTION)

    assert record.stage == BookingStage.READY
    assert len(tracker.records) == 1
    assert tracker.current_stage == BookingStage.TICKET_SELECTION


def test_cannot_transition_out_of_checkout():
    tracker = StageTracker()
    tracker.start(BookingStage.TICKET_SELECTION)
    tracker.transition(BookingStage.CHECKOUT)

    with pytest.raises(InvalidTransitionError):
        tracker.transition(BookingStage.READY)

    assert tracker.current_stage == BookingStage.CHECKOUT
    assert len(tracker.records) == 1


def test_transition_before_start_still_raises_runtime_error():
    tracker = StageTracker()

    with pytest.raises(RuntimeError):
        tracker.transition(BookingStage.READY)

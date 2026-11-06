import sys

import playwright
import pydantic
import dotenv

from app.core.config import settings, validate_settings


def test_python_version():
    assert sys.version_info >= (3, 14)


def test_core_dependencies_import():
    assert playwright
    assert pydantic
    assert dotenv


def test_manual_assistant_mode():
    assert settings.run_mode == "manual_assistant"


def test_event_url_is_configured():
    assert "webook.com" in settings.event_url


def test_settings_validation():
    validate_settings()


from app.core.models import BookingPreferences, TicketCategory


def test_client_booking_preferences():
    preferences = BookingPreferences()

    assert preferences.quantity == 2
    assert preferences.preferred_category == TicketCategory.BRONZE
    assert preferences.fallback_category == TicketCategory.SILVER
    assert preferences.require_adjacent_seats is True
    assert preferences.fallback_requires_approval is True
    assert preferences.payment_is_manual is True
from app.booking.category_policy import (
    CategoryAvailability,
    choose_category,
)
from app.core.models import TicketCategory


def test_bronze_is_selected_first():
    decision = choose_category(
        bronze=CategoryAvailability(2, True),
        silver=CategoryAvailability(2, True),
    )

    assert decision.category == TicketCategory.BRONZE
    assert decision.requires_approval is False


def test_silver_requires_user_approval():
    decision = choose_category(
        bronze=CategoryAvailability(2, False),
        silver=CategoryAvailability(2, True),
    )

    assert decision.category == TicketCategory.SILVER
    assert decision.requires_approval is True


def test_no_category_available():
    decision = choose_category(
        bronze=CategoryAvailability(1, False),
        silver=CategoryAvailability(1, False),
    )

    assert decision.category is None
    assert decision.requires_approval is False



from app.booking.safety_guard import can_continue
from app.core.models import BookingStage


def test_safe_stages_can_continue():
    assert can_continue(BookingStage.READY) is True
    assert can_continue(BookingStage.WAITING_FOR_USER) is True
    assert can_continue(BookingStage.TICKET_SELECTION) is True


def test_checkout_and_terminal_stages_are_blocked():
    assert can_continue(BookingStage.CHECKOUT) is False
    assert can_continue(BookingStage.COMPLETED) is False
    assert can_continue(BookingStage.STOPPED) is False

from app.monitoring.stage_tracker import StageTracker
from app.core.models import BookingStage


def test_stage_tracker_records_transitions():
    tracker = StageTracker()

    tracker.start(BookingStage.READY)
    first_record = tracker.transition(BookingStage.WAITING_FOR_USER)

    assert first_record.stage == BookingStage.READY
    assert first_record.duration_seconds >= 0

    second_record = tracker.stop()

    assert second_record.stage == BookingStage.WAITING_FOR_USER
    assert second_record.duration_seconds >= 0
    assert len(tracker.records) == 2


def test_stage_tracker_cannot_start_twice():
    tracker = StageTracker()
    tracker.start(BookingStage.READY)

    try:
        tracker.start(BookingStage.READY)
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


def test_stage_tracker_cannot_stop_before_start():
    tracker = StageTracker()

    try:
        tracker.stop()
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass
from app.reporting.report_builder import build_report
from app.monitoring.stage_tracker import StageDuration


def test_report_builder_calculates_total_duration():
    records = (
        StageDuration(
            stage=BookingStage.READY,
            duration_seconds=12.5,
        ),
        StageDuration(
            stage=BookingStage.WAITING_FOR_USER,
            duration_seconds=30.0,
        ),
    )

    report = build_report(records)

    assert report["total_duration_seconds"] == 42.5
    assert report["stage_count"] == 2
    assert len(report["stages"]) == 2
    assert report["stages"][0]["stage"] == "ready"

import json

from app.reporting.report_writer import save_report


def test_report_is_saved_as_json(tmp_path):
    report = {
        "total_duration_seconds": 42.5,
        "stage_count": 2,
        "stages": [],
    }

    report_path = save_report(report, str(tmp_path))

    assert report_path.exists()

    saved_data = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert saved_data["total_duration_seconds"] == 42.5
    assert saved_data["stage_count"] == 2
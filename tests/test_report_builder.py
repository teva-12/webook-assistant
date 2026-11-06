from datetime import datetime, timedelta

import pytest

from app.core.models import BookingStage
from app.monitoring.stage_tracker import StageDuration
from app.reporting.report_builder import (
    SAFETY_NOTE,
    build_report,
    determine_session_status,
    format_duration,
)


def make_records(*pairs):
    return tuple(StageDuration(stage=stage, duration_seconds=seconds) for stage, seconds in pairs)


# ---------- format_duration ----------

@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "00:00:00"),
        (9, "00:00:09"),
        (9.9, "00:00:09"),
        (59.999, "00:00:59"),
        (60, "00:01:00"),
        (3661, "01:01:01"),
        (-5, "00:00:00"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


# ---------- generated_at ----------

def test_generated_at_is_present_and_utc_iso_format():
    report = build_report(make_records((BookingStage.READY, 1.0)))

    generated_at = datetime.fromisoformat(report["generated_at"])

    assert generated_at.tzinfo is not None
    assert generated_at.utcoffset() == timedelta(0)


def test_generated_at_is_present_in_empty_report():
    report = build_report(())

    assert datetime.fromisoformat(report["generated_at"]).utcoffset() == timedelta(0)


# ---------- normal session ----------

def test_normal_session_keeps_existing_fields_and_adds_new_ones():
    records = make_records(
        (BookingStage.READY, 12.5),
        (BookingStage.WAITING_FOR_USER, 30.0),
    )

    report = build_report(records)

    # existing fields
    assert "generated_at" in report
    assert report["total_duration_seconds"] == 42.5
    assert report["stage_count"] == 2
    assert len(report["stages"]) == 2
    assert report["stages"][0]["stage"] == "ready"
    assert report["stages"][0]["duration_seconds"] == 12.5

    # new fields
    assert report["total_duration_formatted"] == "00:00:42"
    assert report["final_stage"] == "waiting_for_user"
    assert report["session_status"] == "finished_by_user"
    assert report["safety_stop_reached"] is False
    assert "safety_note" not in report
    assert report["stages"][0]["duration_formatted"] == "00:00:12"


def test_stage_summary_aggregates_repeated_stages():
    records = make_records(
        (BookingStage.READY, 10.0),
        (BookingStage.WAITING_FOR_USER, 20.0),
        (BookingStage.READY, 10.0),
    )

    report = build_report(records)
    summary = {item["stage"]: item for item in report["stage_summary"]}

    assert report["stage_count"] == 3
    assert [item["stage"] for item in report["stage_summary"]] == ["ready", "waiting_for_user"]
    assert summary["ready"]["visits"] == 2
    assert summary["ready"]["total_duration_seconds"] == 20.0
    assert summary["ready"]["total_duration_formatted"] == "00:00:20"
    assert summary["ready"]["percentage_of_session"] == 50.0
    assert summary["waiting_for_user"]["visits"] == 1
    assert summary["waiting_for_user"]["percentage_of_session"] == 50.0


# ---------- empty report ----------

def test_empty_report_does_not_fail():
    report = build_report(())

    assert report["total_duration_seconds"] == 0
    assert report["total_duration_formatted"] == "00:00:00"
    assert report["stage_count"] == 0
    assert report["stages"] == []
    assert report["stage_summary"] == []
    assert report["final_stage"] is None
    assert report["session_status"] == "no_data"
    assert report["safety_stop_reached"] is False


def test_all_zero_durations_do_not_divide_by_zero():
    report = build_report(make_records((BookingStage.READY, 0.0)))

    assert report["stage_summary"][0]["percentage_of_session"] == 0.0


# ---------- checkout is a safety stop, not a purchase ----------

def test_checkout_is_reported_as_safety_stop_only():
    records = make_records(
        (BookingStage.READY, 5.0),
        (BookingStage.TICKET_SELECTION, 4.0),
        (BookingStage.CHECKOUT, 0.0),
    )

    report = build_report(records)

    assert report["final_stage"] == "checkout"
    assert report["session_status"] == "safety_stop_at_checkout"
    assert report["safety_stop_reached"] is True
    assert report["safety_note"] == SAFETY_NOTE
    assert report["total_duration_formatted"] == "00:00:09"
    # Must never be reported as a finished booking or purchase.
    assert "completed" not in report["session_status"]
    assert "booked" not in report["session_status"]


# ---------- session status ----------

@pytest.mark.parametrize(
    "stage, expected",
    [
        (None, "no_data"),
        (BookingStage.READY, "finished_by_user"),
        (BookingStage.WAITING_FOR_USER, "finished_by_user"),
        (BookingStage.TICKET_SELECTION, "finished_by_user"),
        (BookingStage.CHECKOUT, "safety_stop_at_checkout"),
        (BookingStage.STOPPED, "stopped"),
        (BookingStage.COMPLETED, "session_closed"),
    ],
)
def test_determine_session_status(stage, expected):
    assert determine_session_status(stage) == expected
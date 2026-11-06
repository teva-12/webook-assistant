from collections.abc import Sequence
from datetime import datetime, timezone

from app.core.models import BookingStage
from app.monitoring.stage_tracker import StageDuration

STATUS_NO_DATA = "no_data"
STATUS_SAFETY_STOP = "safety_stop_at_checkout"
STATUS_STOPPED = "stopped"
# Session closed at the COMPLETED stage. This does NOT mean a purchase was made.
STATUS_SESSION_CLOSED = "session_closed"
STATUS_FINISHED_BY_USER = "finished_by_user"

SAFETY_NOTE = (
    "Checkout is a safety stop only. This tool does not complete payment "
    "and does not verify whether a purchase was made."
)


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS. Fractions are truncated; negatives become 0."""
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def determine_session_status(final_stage: BookingStage | None) -> str:
    """Derive the session status from the last recorded stage only."""
    if final_stage is None:
        return STATUS_NO_DATA
    if final_stage == BookingStage.CHECKOUT:
        return STATUS_SAFETY_STOP
    if final_stage == BookingStage.STOPPED:
        return STATUS_STOPPED
    if final_stage == BookingStage.COMPLETED:
        return STATUS_SESSION_CLOSED
    return STATUS_FINISHED_BY_USER


def _build_stage_summary(
    records: Sequence[StageDuration], total_duration: float
) -> list[dict]:
    """Aggregate repeated visits to the same stage, in order of first appearance."""
    totals: dict[BookingStage, dict] = {}

    for record in records:
        entry = totals.setdefault(record.stage, {"visits": 0, "seconds": 0.0})
        entry["visits"] += 1
        entry["seconds"] += record.duration_seconds

    summary = []
    for stage, entry in totals.items():
        seconds = round(entry["seconds"], 3)
        percentage = round(seconds / total_duration * 100, 2) if total_duration > 0 else 0.0
        summary.append(
            {
                "stage": stage.value,
                "visits": entry["visits"],
                "total_duration_seconds": seconds,
                "total_duration_formatted": format_duration(seconds),
                "percentage_of_session": percentage,
            }
        )

    return summary


def build_report(records: Sequence[StageDuration]) -> dict:
    total_duration = round(sum(record.duration_seconds for record in records), 3)

    final_stage = records[-1].stage if records else None
    session_status = determine_session_status(final_stage)

    report = {
        # Existing fields (kept unchanged for backward compatibility)
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_duration_seconds": total_duration,
        "stage_count": len(records),
        "stages": [
            {
                "stage": record.stage.value,
                "duration_seconds": record.duration_seconds,
                "duration_formatted": format_duration(record.duration_seconds),
            }
            for record in records
        ],
        # New fields
        "total_duration_formatted": format_duration(total_duration),
        "final_stage": final_stage.value if final_stage is not None else None,
        "session_status": session_status,
        "safety_stop_reached": session_status == STATUS_SAFETY_STOP,
        "stage_summary": _build_stage_summary(records, total_duration),
    }

    if session_status == STATUS_SAFETY_STOP:
        report["safety_note"] = SAFETY_NOTE

    return report
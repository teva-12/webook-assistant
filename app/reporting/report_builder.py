from datetime import datetime, timezone

from app.monitoring.stage_tracker import StageDuration


def build_report(records: tuple[StageDuration, ...]) -> dict:
    stages = [
        {
            "stage": record.stage.value,
            "duration_seconds": record.duration_seconds,
        }
        for record in records
    ]

    total_duration = round(
        sum(record.duration_seconds for record in records),
        3,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_duration_seconds": total_duration,
        "stage_count": len(stages),
        "stages": stages,
    }
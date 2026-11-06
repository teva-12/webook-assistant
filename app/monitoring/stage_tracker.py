
from dataclasses import dataclass
from time import monotonic

from app.core.models import BookingStage
from app.monitoring.stage_transitions import validate_transition


@dataclass(frozen=True)
class StageDuration:
    stage: BookingStage
    duration_seconds: float


class StageTracker:
    def __init__(self):
        self._current_stage = None
        self._started_at = None
        self._records = []

    def start(self, stage: BookingStage) -> None:
        if self._current_stage is not None:
            raise RuntimeError("Tracker is already running.")

        self._current_stage = stage
        self._started_at = monotonic()

    def transition(self, next_stage: BookingStage) -> StageDuration:
        if self._current_stage is None:
            raise RuntimeError("Tracker has not started.")

        validate_transition(self._current_stage, next_stage)

        duration = round(monotonic() - self._started_at, 3)

        record = StageDuration(
            stage=self._current_stage,
            duration_seconds=duration,
        )

        self._records.append(record)
        self._current_stage = next_stage
        self._started_at = monotonic()

        return record

    def stop(self) -> StageDuration:
        if self._current_stage is None:
            raise RuntimeError("Tracker is not running.")

        record = StageDuration(
            stage=self._current_stage,
            duration_seconds=round(monotonic() - self._started_at, 3),
        )

        self._records.append(record)
        self._current_stage = None
        self._started_at = None

        return record

    @property
    def current_stage(self) -> BookingStage | None:
        return self._current_stage

    @property
    def records(self) -> tuple[StageDuration, ...]:
        return tuple(self._records)

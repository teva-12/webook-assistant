from app.core.models import BookingStage


SAFE_STAGES = {
    BookingStage.READY,
    BookingStage.WAITING_FOR_USER,
    BookingStage.TICKET_SELECTION,
}


def can_continue(stage: BookingStage) -> bool:
    return stage in SAFE_STAGES
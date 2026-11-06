
from app.core.models import BookingStage


class InvalidTransitionError(ValueError):
    """Raised when a stage transition is not permitted."""


# Deny-by-default transition allowlist.
ALLOWED_TRANSITIONS: dict[BookingStage, frozenset[BookingStage]] = {
    BookingStage.READY: frozenset({
        BookingStage.WAITING_FOR_USER,
        BookingStage.TICKET_SELECTION,
        BookingStage.CHECKOUT,
    }),
    BookingStage.WAITING_FOR_USER: frozenset({
        BookingStage.READY,
        BookingStage.TICKET_SELECTION,
        BookingStage.CHECKOUT,
    }),
    BookingStage.TICKET_SELECTION: frozenset({
        BookingStage.READY,
        BookingStage.WAITING_FOR_USER,
        BookingStage.CHECKOUT,
    }),
    BookingStage.CHECKOUT: frozenset(),
    BookingStage.COMPLETED: frozenset(),
    BookingStage.STOPPED: frozenset(),
}


def is_transition_allowed(
    current: BookingStage,
    target: BookingStage,
) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def validate_transition(
    current: BookingStage,
    target: BookingStage,
) -> None:
    if current == target:
        raise InvalidTransitionError(
            f"Already in stage '{current.value}'."
        )

    if not is_transition_allowed(current, target):
        raise InvalidTransitionError(
            f"Transition from '{current.value}' "
            f"to '{target.value}' is not allowed."
        )

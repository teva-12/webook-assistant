from enum import Enum

from pydantic import BaseModel, Field


class BookingStage(str, Enum):
    READY = "ready"
    WAITING_FOR_USER = "waiting_for_user"
    TICKET_SELECTION = "ticket_selection"
    CHECKOUT = "checkout"
    COMPLETED = "completed"
    STOPPED = "stopped"


class TicketCategory(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    ROYAL = "royal"


class BookingPreferences(BaseModel):
    quantity: int = Field(default=2, ge=1, le=3)
    preferred_category: TicketCategory = TicketCategory.BRONZE
    fallback_category: TicketCategory = TicketCategory.SILVER
    preferred_zone: str | None = None
    require_adjacent_seats: bool = True
    fallback_requires_approval: bool = True
    payment_is_manual: bool = True

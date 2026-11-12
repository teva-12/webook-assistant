from types import SimpleNamespace

from app.telegram_bot import _allowed, _reset_booking_preferences


def _update(chat_id):
    return SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id))


def test_bot_denies_every_chat_when_allowlist_is_empty(monkeypatch):
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    assert _allowed(_update(12345)) is False


def test_bot_allows_only_chat_ids_in_comma_separated_allowlist(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345, 67890")

    assert _allowed(_update(12345)) is True
    assert _allowed(_update(67890)) is True
    assert _allowed(_update(99999)) is False


def test_bot_denies_updates_without_effective_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    assert _allowed(SimpleNamespace(effective_chat=None)) is False


def test_new_booking_clears_previous_preferences_and_fallback_approval():
    state = {
        "event_url": "https://webook.com/en/events/test",
        "preferred_category": "Bronze",
        "quantity": 2,
        "adjacent": True,
        "preferred_area": "Layer 2",
        "fallback_category": "Silver",
        "fallback_approved": True,
        "handoff_reported_by_user": True,
        "handoff_stage": "payment_review_by_customer",
    }

    _reset_booking_preferences(state)

    assert state["event_url"] == "https://webook.com/en/events/test"
    assert state["step"] == "category"
    assert state["handoff_reported_by_user"] is False
    assert "fallback_approved" not in state
    assert "fallback_category" not in state
    assert "preferred_category" not in state
    assert "quantity" not in state

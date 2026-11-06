import app.main as main


def test_silver_fallback_can_be_rejected_by_user(monkeypatch):
    ticket_counts = iter([2, 2])
    answers = iter([False, True, False])

    monkeypatch.setattr(
        main,
        "ask_ticket_count",
        lambda category: next(ticket_counts),
    )
    monkeypatch.setattr(
        main.Confirm,
        "ask",
        lambda *args, **kwargs: next(answers),
    )

    result = main.evaluate_ticket_options()

    assert result["recommended_category"] == "silver"
    assert result["approval_required"] is True
    assert result["user_approved"] is False
    assert result["result"] == "rejected"
    assert result["manual_input"] is True
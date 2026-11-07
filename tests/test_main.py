import app.main as main


def test_silver_fallback_can_be_rejected_by_user(monkeypatch):
    ticket_counts = iter([2, 2])
    prompt_answers = iter(["Area 2", "Bronze", "Silver"])
    confirm_answers = iter([True, False, True, False])

    monkeypatch.setattr(main.IntPrompt, "ask", lambda *args, **kwargs: 2)
    monkeypatch.setattr(main.Prompt, "ask", lambda *args, **kwargs: next(prompt_answers))
    monkeypatch.setattr(main, "ask_ticket_count", lambda category: next(ticket_counts))
    monkeypatch.setattr(main.Confirm, "ask", lambda *args, **kwargs: next(confirm_answers))

    result = main.evaluate_ticket_options(["Bronze", "Silver", "Gold"])

    assert result["recommended_category"] == "silver"
    assert result["approval_required"] is True
    assert result["user_approved"] is False
    assert result["result"] == "fallback_rejected"
    assert result["quantity_requested"] == 2
    assert result["preferred_zone"] == "Area 2"
    assert result["manual_input"] is True

from app.monitoring.page_inspector import (
    build_page_inspection,
    extract_explicit_availability_evidence,
    extract_visible_categories,
)


def test_extracts_visible_category_prices_with_line_breaks_and_commas():
    text = """Ticket types
    RO
    Royal
    3,450
    DI
    Diamond
    2,875
    BR
    Bronze
    405"""

    categories = extract_visible_categories(text)

    assert [(item.name, item.price_sar, item.price_display) for item in categories] == [
        ("Bronze", 405, "405"),
        ("Diamond", 2875, "2,875"),
        ("Royal", 3450, "3,450"),
    ]


def test_does_not_infer_availability_when_no_explicit_phrase_exists():
    assert extract_explicit_availability_evidence(
        "Bronze 405 Silver 865"
    ) == ()


def test_records_explicit_wording_without_claiming_queue_status():
    result = build_page_inspection(
        "Event",
        "https://webook.com/en/events/test",
        "Tickets available for Fun members after 3 hours",
    )

    assert result.availability_evidence == ("tickets available",)
    assert "queue_status" not in result.to_dict()



def test_extracts_euro_ticket_prices_without_relabeling_them_as_sar():
    text = """Ticket types
    BR
    Bronze ticket
    €70.26
    SI
    Silver ticket
    €94.07
    GO
    Gold ticket
    €130.99"""

    categories = extract_visible_categories(text)

    assert [(item.name, item.price_sar, item.price_display, item.currency) for item in categories] == [
        ("Bronze", None, "€70.26", "EUR"),
        ("Silver", None, "€94.07", "EUR"),
        ("Gold", None, "€130.99", "EUR"),
    ]

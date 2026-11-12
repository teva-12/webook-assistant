from app.booking.seat_map import (
    HoverObservation,
    find_adjacent_visible_pairs,
    parse_visible_seat_tooltip,
)


def test_parse_explicit_available_seat():
    seat = parse_visible_seat_tooltip("Bronze · Row A · Seat 12 · Available")
    assert seat is not None
    assert (seat.row, seat.number, seat.category) == ("A", 12, "Bronze")


def test_unknown_status_is_not_assumed_available():
    assert parse_visible_seat_tooltip("Bronze · Row A · Seat 12") is None


def test_sold_seat_is_rejected():
    assert parse_visible_seat_tooltip("Bronze · Row A · Seat 12 · Sold") is None


def test_pair_requires_same_row_same_category_and_consecutive_numbers():
    observations = [
        HoverObservation(1, 1, "Bronze Row A Seat 12 Available"),
        HoverObservation(2, 1, "Bronze Row A Seat 13 Available"),
        HoverObservation(3, 1, "Bronze Row A Seat 14 Sold"),
        HoverObservation(4, 1, "Bronze Row B Seat 14 Available"),
        HoverObservation(5, 1, "Silver Row A Seat 14 Available"),
    ]
    pairs = find_adjacent_visible_pairs(observations, category="Bronze")
    assert len(pairs) == 1
    assert (pairs[0].first.number, pairs[0].second.number) == (12, 13)


def test_category_missing_is_not_guessed():
    observations = [
        HoverObservation(1, 1, "Row A Seat 12 Available"),
        HoverObservation(2, 1, "Row A Seat 13 Available"),
    ]
    assert find_adjacent_visible_pairs(observations, category="Bronze") == []

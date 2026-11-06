
import json

from app.reporting.report_writer import save_report, save_html_report


def sample_report():
    return {
        "generated_at": "2026-11-06T17:37:15+00:00",
        "total_duration_seconds": 7.199,
        "total_duration_formatted": "00:00:07",
        "stage_count": 2,
        "final_stage": "checkout",
        "session_status": "safety_stop_at_checkout",
        "safety_stop_reached": True,
        "safety_note": (
            "Checkout is a safety stop only. "
            "No payment or purchase was performed."
        ),
        "stages": [
            {
                "stage": "ready",
                "duration_seconds": 3.3,
                "duration_formatted": "00:00:03",
            },
            {
                "stage": "checkout",
                "duration_seconds": 3.899,
                "duration_formatted": "00:00:03",
            },
        ],
        "stage_summary": [
            {
                "stage": "ready",
                "visits": 1,
                "total_duration_formatted": "00:00:03",
                "percentage_of_session": 45.84,
            },
            {
                "stage": "checkout",
                "visits": 1,
                "total_duration_formatted": "00:00:03",
                "percentage_of_session": 54.16,
            },
        ],
    }


def test_save_report_creates_valid_json(tmp_path):
    report = sample_report()

    report_path = save_report(report, str(tmp_path))

    assert report_path.exists()
    assert report_path.name == "booking_report.json"

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved_report == report


def test_save_html_report_creates_file(tmp_path):
    report = sample_report()

    report_path = save_html_report(report, str(tmp_path))

    assert report_path.exists()
    assert report_path.name == "booking_report.html"


def test_html_report_contains_session_information(tmp_path):
    report = sample_report()

    report_path = save_html_report(report, str(tmp_path))
    content = report_path.read_text(encoding="utf-8")

    assert "Booking Assistant" in content
    assert "Safety Stop Activated" in content
    assert "Stage Summary" in content
    assert "Session Timeline" in content
    assert "ready" in content
    assert "checkout" in content
    assert "No payment or purchase was performed." in content


def test_html_report_handles_empty_data(tmp_path):
    report = {
        "session_status": "no_data",
        "safety_stop_reached": False,
        "stages": [],
        "stage_summary": [],
    }

    report_path = save_html_report(report, str(tmp_path))
    content = report_path.read_text(encoding="utf-8")

    assert report_path.exists()
    assert "No stage data available." in content
    assert "No session activity recorded." in content
def test_html_report_contains_ticket_evaluation_results(tmp_path):
    report = sample_report()

    report["ticket_evaluations"] = [
        {
            "bronze_available_count": 2,
            "bronze_adjacent_seats": True,
            "silver_available_count": 0,
            "silver_adjacent_seats": False,
            "recommended_category": "bronze",
            "result": "approved",
        },
        {
            "bronze_available_count": 0,
            "bronze_adjacent_seats": False,
            "silver_available_count": 2,
            "silver_adjacent_seats": True,
            "recommended_category": "silver",
            "result": "approved",
        },
    ]

    report_path = save_html_report(report, str(tmp_path))
    content = report_path.read_text(encoding="utf-8")

    assert "Ticket Evaluation Results" in content
    assert "Bronze Count" in content
    assert "Silver Count" in content
    assert "BRONZE" in content
    assert "SILVER" in content
    assert content.count("Approved") == 2
    assert "No" in content
    assert "Yes" in content
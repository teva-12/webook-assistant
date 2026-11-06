import html
import json
from pathlib import Path


def save_report(
    report: dict,
    output_dir: str = "reports",
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    report_path = directory / "booking_report.json"

    report_path.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    return report_path


def save_html_report(
    report: dict,
    output_dir: str = "reports",
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    def safe(value):
        return html.escape(str(value))

    status = report.get("session_status", "no_data")

    status_labels = {
        "no_data": "No Session Data",
        "safety_stop_at_checkout": "Safety Stop Reached",
        "stopped": "Session Stopped",
        "session_closed": "Session Closed",
        "finished_by_user": "Finished by User",
    }

    status_label = status_labels.get(status, "Unknown Status")
    is_safety_stop = report.get("safety_stop_reached", False)

    status_class = (
        "warning" if is_safety_stop
        else "success" if status == "finished_by_user"
        else "neutral"
    )

    # Stage summary rows
    stage_rows = ""

    for item in report.get("stage_summary", []):
        stage_rows += f"""
        <tr>
            <td>{safe(item.get("stage", "Unknown"))}</td>
            <td>{safe(item.get("visits", 0))}</td>
            <td>{safe(item.get("total_duration_formatted", "00:00:00"))}</td>
            <td>
                <div class="progress-cell">
                    <div class="progress-track">
                        <div class="progress-fill"
                             style="width: {max(0, min(100, float(item.get('percentage_of_session', 0))))}%">
                        </div>
                    </div>
                    <span>{safe(item.get("percentage_of_session", 0))}%</span>
                </div>
            </td>
        </tr>
        """

    # Session timeline rows
    timeline_rows = ""

    for index, item in enumerate(report.get("stages", []), start=1):
        timeline_rows += f"""
        <tr>
            <td>{index:02d}</td>
            <td>{safe(item.get("stage", "Unknown"))}</td>
            <td>{safe(item.get("duration_formatted", "00:00:00"))}</td>
            <td>{safe(item.get("duration_seconds", 0))} sec</td>
        </tr>
        """

    if not stage_rows:
        stage_rows = (
            '<tr><td colspan="4">No stage data available.</td></tr>'
        )

    if not timeline_rows:
        timeline_rows = (
            '<tr><td colspan="4">No session activity recorded.</td></tr>'
        )

    # Safety notice
    safety_section = ""

    if is_safety_stop:
        safety_note = safe(
            report.get(
                "safety_note",
                "Checkout is a safety stop. No payment or purchase was performed.",
            )
        )

        safety_section = f"""
        <section class="safety-notice">
            <div class="notice-icon">!</div>
            <div>
                <h3>Safety Stop Activated</h3>
                <p>{safety_note}</p>
            </div>
        </section>
        """

    # Ticket evaluation rows
    evaluation_rows = ""

    for index, item in enumerate(
        report.get("ticket_evaluations", []),
        start=1,
    ):
        evaluation_rows += f"""
        <tr>
            <td>{index}</td>
            <td>{safe(item.get("bronze_available_count", 0))}</td>
            <td>{safe("Yes" if item.get("bronze_adjacent_seats") else "No")}</td>
            <td>{safe(item.get("silver_available_count", 0))}</td>
            <td>{safe("Yes" if item.get("silver_adjacent_seats") else "No")}</td>
            <td>{safe((item.get("recommended_category") or "None").upper())}</td>
            <td>{safe(item.get("result", "Not selected").replace("_", " ").title())}</td>
        </tr>
        """

    if not evaluation_rows:
        evaluation_rows = (
            '<tr><td colspan="7">No ticket evaluations recorded.</td></tr>'
        )

    # Report information
    generated_at = safe(
        report.get("generated_at", "Not available")
    )

    total_duration = safe(
        report.get("total_duration_formatted", "00:00:00")
    )

    total_seconds = safe(
        report.get("total_duration_seconds", 0)
    )

    stage_count = safe(
        report.get("stage_count", 0)
    )

    final_stage = safe(
        report.get("final_stage") or "None"
    )

    # HTML document
    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Booking Assistant session report">
    <title>Booking Assistant | Session Report</title>

    <style>
        :root {{
            color-scheme: dark;
            --bg: #0b1020;
            --panel: #131b2e;
            --panel-light: #19243a;
            --text: #edf2ff;
            --muted: #94a3b8;
            --accent: #65a7ff;
            --border: #293750;
            --warning: #fbbf24;
            --success: #34d399;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 36px 20px;
            background: var(--bg);
            color: var(--text);
            font-family: Inter, "Segoe UI", Arial, sans-serif;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1050px;
            margin: auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
        }}

        .eyebrow {{
            color: var(--accent);
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}

        h1 {{
            margin: 5px 0;
            font-size: clamp(26px, 5vw, 36px);
        }}

        .subtitle,
        .muted {{
            color: var(--muted);
            font-size: 13px;
        }}

        .status {{
            padding: 9px 15px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 700;
            white-space: nowrap;
            margin-bottom: 12px;
            text-align: center;
        }}

        .warning {{
            background: #422f12;
            color: var(--warning);
        }}

        .success {{
            background: #103b30;
            color: var(--success);
        }}

        .neutral {{
            background: #26344b;
            color: #cbd5e1;
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 22px;
        }}

        .card,
        .section {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 15px;
        }}

        .card {{
            padding: 21px;
        }}

        .metric-label {{
            color: var(--muted);
            font-size: 13px;
        }}

        .metric-value {{
            margin-top: 8px;
            font-size: 27px;
            font-weight: 750;
            overflow-wrap: anywhere;
        }}

        .section {{
            padding: 23px;
            margin-bottom: 20px;
        }}

        h2 {{
            margin: 0 0 18px;
            font-size: 18px;
        }}

        .safety-notice {{
            display: flex;
            gap: 16px;
            padding: 20px;
            margin-bottom: 20px;
            background: #302514;
            border: 1px solid #76551b;
            border-radius: 15px;
        }}

        .notice-icon {{
            display: grid;
            place-items: center;
            flex: 0 0 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--warning);
            color: #1c1609;
            font-weight: 900;
        }}

        .safety-notice h3 {{
            margin: 0 0 5px;
            color: var(--warning);
        }}

        .safety-notice p {{
            margin: 0;
            color: #f5e6c5;
            font-size: 14px;
        }}

        .table-wrap {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 520px;
            text-align: left;
        }}

        th,
        td {{
            padding: 14px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }}

        th {{
            color: var(--muted);
            font-weight: 600;
        }}

        .progress-cell {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .progress-track {{
            width: 100px;
            height: 7px;
            overflow: hidden;
            border-radius: 10px;
            background: var(--panel-light);
        }}

        .progress-fill {{
            height: 100%;
            border-radius: 10px;
            background: var(--accent);
        }}

        footer {{
            padding: 15px 0;
            color: var(--muted);
            font-size: 12px;
            text-align: center;
        }}

        .print-button {{
            padding: 10px 16px;
            border: 1px solid var(--border);
            border-radius: 9px;
            background: var(--panel-light);
            color: var(--text);
            cursor: pointer;
            font-weight: 600;
        }}

        @media (max-width: 650px) {{
            body {{
                padding: 22px 12px;
            }}

            header {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .metrics {{
                grid-template-columns: 1fr;
            }}

            .metric-value {{
                font-size: 23px;
            }}

            .section {{
                padding: 16px;
            }}
        }}

        @media print {{
            :root {{
                color-scheme: light;
                --bg: white;
                --panel: white;
                --text: #111827;
                --muted: #475569;
                --border: #d1d5db;
                --panel-light: #e5e7eb;
            }}

            body {{
                padding: 0;
            }}

            .print-button {{
                display: none;
            }}

            .card,
            .section {{
                break-inside: avoid;
            }}
        }}
    </style>
</head>

<body>
    <main class="container">

        <header>
            <div>
                <div class="eyebrow">Session Analytics</div>
                <h1>Booking Assistant</h1>
                <div class="subtitle">
                    Session performance and activity report
                </div>
            </div>

            <div>
                <div class="status {status_class}">
                    {safe(status_label)}
                </div>

                <button class="print-button" onclick="window.print()">
                    Print / Save PDF
                </button>
            </div>
        </header>

        {safety_section}

        <section class="section">
            <h2>Ticket Evaluation Results</h2>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Bronze Count</th>
                            <th>Bronze Adjacent</th>
                            <th>Silver Count</th>
                            <th>Silver Adjacent</th>
                            <th>Recommendation</th>
                            <th>Decision</th>
                        </tr>
                    </thead>

                    <tbody>
                        {evaluation_rows}
                    </tbody>
                </table>
            </div>
        </section>

        <section class="metrics">
            <div class="card">
                <div class="metric-label">Total Duration</div>
                <div class="metric-value">{total_duration}</div>
                <div class="muted">{total_seconds} seconds</div>
            </div>

            <div class="card">
                <div class="metric-label">Recorded Stages</div>
                <div class="metric-value">{stage_count}</div>
                <div class="muted">Stage records in this session</div>
            </div>

            <div class="card">
                <div class="metric-label">Final Stage</div>
                <div class="metric-value">{final_stage}</div>
                <div class="muted">Last recorded stage</div>
            </div>
        </section>

        <section class="section">
            <h2>Stage Summary</h2>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Stage</th>
                            <th>Visits</th>
                            <th>Total Time</th>
                            <th>Session Share</th>
                        </tr>
                    </thead>

                    <tbody>
                        {stage_rows}
                    </tbody>
                </table>
            </div>
        </section>

        <section class="section">
            <h2>Session Timeline</h2>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Stage</th>
                            <th>Duration</th>
                            <th>Exact Time</th>
                        </tr>
                    </thead>

                    <tbody>
                        {timeline_rows}
                    </tbody>
                </table>
            </div>
        </section>

        <section class="section">
            <h2>Report Information</h2>

            <div class="muted">Generated at (UTC)</div>
            <div>{generated_at}</div>
        </section>

        <footer>
            Booking Assistant · Manual Session Tracking ·
            No automated purchase or payment was performed.
        </footer>

    </main>
</body>
</html>
"""

    report_path = directory / "booking_report.html"
    report_path.write_text(document, encoding="utf-8")

    return report_path
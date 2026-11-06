import json
from pathlib import Path


def save_report(
    report: dict,
    output_dir: str = "reports",
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    filename = "booking_report.json"
    report_path = directory / filename

    report_path.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    return report_path
# Webook Booking Assistant

A Python proof of concept for manually tracking ticket-booking sessions and generating session reports.

## Current Features

- Manual booking-stage tracking.
- Booking preferences for Bronze and Silver ticket categories.
- Explicit user approval for fallback category selection.
- Stage duration measurement.
- Session analytics and stage summaries.
- JSON session reports.
- Responsive HTML session reports.
- Print or save HTML reports as PDF.
- Safety stop at checkout.

## Safety Boundaries

This project is a manual session-tracking assistant. It does not automate ticket purchases or interact with Webook automatically.

- No queue bypass or priority manipulation.
- No CAPTCHA or anti-bot circumvention.
- No unauthorized automated access to Webook.
- No collection or storage of login credentials.
- No automatic payment or ticket purchase.
- All booking and payment actions remain under user control.
- Checkout is a safety stop, not confirmation of a successful purchase.

## Requirements

- Python 3.14+
- Playwright
- Pydantic
- python-dotenv
- pytest
- Rich

## Setup

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Activate it.

   **Windows PowerShell:**

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Install Chromium:

   ```bash
   python -m playwright install chromium
   ```

## Configuration

Copy `.env.example` to `.env` and review the configuration values.

Do not commit `.env` or any credentials to version control.

## Run

```bash
python -m app.main
```

## Tests

Run the test suite:

```bash
python -m pytest -v
```

## Reports

After a session ends, the application generates two reports in the `reports/` directory:

- `booking_report.json` — structured session data.
- `booking_report.html` — a responsive visual dashboard containing session metrics, stage summaries, and a timeline.

Open `booking_report.html` in a browser. Use the **Print / Save PDF** control to print the report or save it as a PDF.

Generated reports are local output files and are not automatically uploaded to GitHub.

## Project Status

**Phase 1 — Manual assistant core and session reporting.**

This is a proof of concept, not a production-ready ticket-booking or purchasing system.
# Webook Booking Assistant

A Python proof of concept for manually tracking a ticket-booking session.

## Current Features

- Manual booking-stage tracking.
- Booking preferences for Bronze and Silver categories.
- Explicit approval for fallback category selection.
- Stage duration measurement.
- JSON session reports.
- Safety stop at checkout.

## Safety Boundaries

- No queue bypass or priority manipulation.
- No CAPTCHA or anti-bot circumvention.
- No automated access to Webook.
- No collection or storage of login credentials.
- No automatic payment or ticket purchase.
- All booking and payment actions remain under user control.

## Requirements

- Python 3.14+
- Playwright
- Pydantic
- python-dotenv
- pytest

## Setup

1. Create a virtual environment.
2. Activate it.
3. Install dependencies:

    pip install -r requirements.txt

4. Install Chromium:

    python -m playwright install chromium

## Run

    python -m app.main

## Tests

    python -m pytest -v

## Reports

Generated session reports are saved in:

reports/booking_report.json

## Project Status

Phase 1 — Manual assistant core and reporting.
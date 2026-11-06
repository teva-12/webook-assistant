# Webook Booking Assistant

A controlled browser automation proof of concept for monitoring the official Webook booking flow.

## Current Scope

- Open the configured event page using Playwright.
- Monitor visible booking stages.
- Measure time spent in each stage.
- Notify the user when manual action is required.
- Keep login and payment under the user's control.

## Safety Boundaries

- No queue bypass or priority manipulation.
- No CAPTCHA or anti-bot circumvention.
- No forged, extracted, or replayed authentication tokens.
- No excessive requests or parallel sessions.
- No automatic payment or final purchase.
- Stop when a bot challenge or unexpected state is detected.

## Current Mode

`monitor_only`

## Requirements

- Python 3.14+
- Playwright
- Pydantic
- python-dotenv
- pytest

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Install Chromium with `python -m playwright install chromium`.

## Run Tests

`python -m pytest -v`

## Project Status

Phase 0 — Environment and project foundation.

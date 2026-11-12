# Changelog

All notable project changes are documented here.

## [1.0.0] - 2026-11-12

### Added
- Telegram commands for configuring and reviewing a Webook event workflow.
- A visible persistent browser session for the user to operate the official website.
- Visible event-page inspection and ticket category/price reporting.
- Seat-map screenshots and visible tooltip diagnostics.
- Per-chat booking preferences and session state.
- Telegram chat ID lookup and fail-closed chat allowlisting.
- Automated tests and a GitHub Actions test workflow.

### Safety and scope
- Authentication, official queues, CAPTCHA, seat selection, checkout, and payment remain manual.
- Seat-map scanning is diagnostic only; it does not guarantee availability or physical adjacency.
- The assistant does not submit orders or claim that a booking or payment succeeded.

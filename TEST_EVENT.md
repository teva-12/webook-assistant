# Generic Webook assistant test — Aseel Hameem at Vocally Riyadh

Test event URL:
https://webook.com/en/sa/ruh/music-events/events/aseel-hameem-concert-vocally-tickets-837762

Use this event only as a test fixture. The same application can open another official Webook event URL through menu option **8**; it is not hard-coded to this concert.

## What this build does

1. Opens the user-provided official Webook event URL in a visible persistent browser.
2. The user signs in and completes any official queue/waiting steps manually.
3. Expands the first numbered ticket-type disclosure when present and reads visible ticket names/prices.
4. Lets the user choose quantity (1–3), a preferred area/section, a preferred category, and a fallback category.
5. Evaluates manually entered visible inventory and whether the requested adjacent-seat condition was visually confirmed.
6. Recommends the preferred category first; fallback requires explicit approval.
7. The user selects seats on Webook's visible seat map and proceeds through the official flow manually.
8. The assistant's checkout stage is a handoff. The user reviews the order and pays directly on Webook.

## Test steps

1. Back up your current `.env` file.
2. Set `EVENT_URL` to the test URL above and `EVENT_NAME=Aseel Hameem at Vocally Riyadh`.
3. Run `python -m app.main`.
4. Choose **5** to open the event, then sign in yourself if requested.
5. Complete any official queue step yourself.
6. Choose **7** to inspect visible ticket types and prices.
7. Choose **2** when you are waiting for the official booking flow; after the site opens the ticket selection stage, choose **3**.
8. Choose **6**, then select quantity, area, preferred category, fallback, and enter only inventory/adjacency that you can actually see.
9. In the browser, manually choose the seats and continue. When the payment page appears, return to the CLI and choose **4** to record the payment handoff and stop.
10. Pay only on Webook yourself if you decide to proceed. Reaching the payment page is not a confirmed booking.

## Safety and limits

- Official Webook login and queue are user-controlled. No queue bypass, priority manipulation, CAPTCHA bypass, hidden API calls, cookie/token extraction, or high-frequency refresh.
- The app does not automatically select seats, click `Next`, submit an order, or pay. The user selects seats and continues manually.
- Ticket prices are extracted from visible page text. Currency is preserved as displayed; no currency conversion is inferred.
- Counts and seat adjacency are not reliably established from category/price text. The user must verify them on the seat map.
- The current build is a local CLI + visible browser prototype. Telegram chat control/notifications are not implemented yet; Telegram environment variables are placeholders only.

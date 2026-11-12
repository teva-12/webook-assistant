# Webook Booking Assistant

A local Python assistant with a Telegram interface and a visible Playwright browser for official Webook event pages.

## Implemented

- Telegram `/start` and `/help` commands.
- Accepts an official `https://webook.com/.../events/...` link in chat and makes it the active event for that chat. Changing the event clears the previous event's ticket preferences.
- `/book` collects preferred ticket category, quantity (1–3), adjacency preference, and preferred area/layer.
- Saves each Telegram chat's state in `data/telegram_sessions.json`.
- `/open` opens the active event in a visible Chromium browser on the same Windows computer running the bot.
- `/inspect` reads visible page text and reports category/price pairs when detectable.
- `/status`, `/cancel`, and `/payment` commands.
- Currency display is preserved; no currency conversion or invented availability.

## Important boundary

The browser is visible. The customer must sign in, complete any official queue/CAPTCHA, choose the layer and zoom, review and select seats, verify the order, and pay. The program does not automate queue controls, CAPTCHA, seat clicks, order submission, or payment. `/scan` is diagnostic only; `/map` shares a screenshot. The `/payment` command only records that the customer says they reached that stage; it does not verify a booking.

## Setup on Windows

1. Install Python 3.14.
2. Create a Telegram bot with Telegram's official `@BotFather` and copy its token.
3. Put the token in `.env`:

   `TELEGRAM_BOT_TOKEN=YOUR_TOKEN_HERE`

   Keep `TELEGRAM_CHAT_ID=` blank unless you want to restrict the bot to one chat. Never upload `.env` or share the token.
4. Install Python dependencies:

   `\.venv\Scripts\python.exe -m pip install -r requirements.txt`
5. Install Chromium once by running `setup_browser.bat`.
6. Start the Telegram bot by running `run_telegram_bot.bat`.
7. Open your bot in Telegram and press Start.

The bot and browser must run on the same computer for `/open` and `/inspect`.

## Telegram flow

1. `/start`
2. Send the Rashed Al Majid Webook event URL (or another official event URL).
3. `/book`, then choose category, quantity, adjacency, and type the preferred area/layer.
4. `/open`; complete sign-in and any queue yourself in the visible browser.
5. `/inspect` to read visible category/price text.
6. On the seat map, choose the layer and zoom manually. Use `/map` to send the visible map to Telegram, or `/scan` to collect visible hover-tooltip text.
7. Review and select seats manually on Webook; the app does not infer availability or adjacency from canvas pixels.
8. Use `/payment` only after you personally reach the payment page. Review and pay directly on Webook.

## Tests

`\.venv\Scripts\python.exe -m pytest -v`

## Configuration

See `.env.example`. The target event defaults to the Rashed Al Majid event supplied for this project.


### فحص خريطة المقاعد (معايرة أولية)

بعد فتح الفعالية وتسجيل الدخول وإنهاء الـQueue يدويًا، انتقل بنفسك إلى خريطة المقاعد، واختر Layer 2 وكبّر المنطقة المطلوبة. أرسل `/scan` في Telegram. الأمر يحرّك مؤشر الماوس على نقاط متباعدة داخل أكبر Canvas ظاهر ويلتقط النصوص التي يعرضها الموقع عند المرور، دون الضغط على أي مقعد أو اختيار أي شيء. هذه خطوة تشخيصية أولية وليست اختيارًا آليًا للمقاعد؛ يلزم التحقق من صيغة Tooltip الفعلية قبل بناء منطق تحديد المقاعد المتجاورة.

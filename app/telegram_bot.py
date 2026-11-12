"""Telegram interface for the Webook manual booking assistant.

The bot gathers a customer's preferences, opens the official event page in a
visible local browser, and reports only information visible on that page.
The customer handles Webook authentication, queue, seat selection, order
confirmation, and payment. It never automates seat-map clicks or checkout.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters,
)

# Load .env before importing modules that read settings at import time.
load_dotenv()
from app.browser.launcher import (  # noqa: E402
    capture_seat_map_screenshot, inspect_visible_event_page, open_event_page, scan_visible_seat_map, validate_event_url,
)
from app.core.config import settings  # noqa: E402
from app.booking.seat_map import (
    parse_visible_seat_tooltip,
    find_adjacent_visible_pairs,
)
log = logging.getLogger(__name__)
_BROWSER_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="webook-browser")
DATA_FILE = Path(os.getenv("BOT_STATE_FILE", "data/telegram_sessions.json"))
CATEGORIES = ("Bronze", "Silver", "Gold", "Platinum", "Diamond", "Royal")


def _load_all_state() -> dict:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_all_state(data: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def _user_state(chat_id: int) -> dict:
    return _load_all_state().get(str(chat_id), {})


def _set_user_state(chat_id: int, state: dict) -> None:
    all_state = _load_all_state()
    all_state[str(chat_id)] = state
    _save_all_state(all_state)


def _reset_booking_preferences(state: dict) -> None:
    """Start a fresh preference flow without carrying approval from an old request."""
    for key in (
        "step",
        "preferred_category",
        "quantity",
        "adjacent",
        "preferred_area",
        "fallback_category",
        "fallback_approved",
        "handoff_stage",
    ):
        state.pop(key, None)
    state["step"] = "category"
    state["handoff_reported_by_user"] = False


def _allowed(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    allowed_ids = {
        value.strip()
        for value in os.getenv("TELEGRAM_CHAT_ID", "").split(",")
        if value.strip()
    }
    # Fail closed: an empty allowlist must never make a personal bot public.
    return str(chat.id) in allowed_ids


def _event_name(url: str) -> str:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    # Remove common trailing numeric Webook identifiers from the display label.
    slug = __import__("re").sub(r"-\d+$", "", slug)
    return slug.replace("-", " ").title() or "Webook Event"


def _reply_target(update: Update):
    return update.effective_message


def _preferences_summary(state: dict) -> str:
    fallback = state.get("fallback_category")
    fallback_text = (
        f"{fallback} ({'موافق عليه' if state.get('fallback_approved') else 'غير مسموح'})"
        if fallback else "لا يوجد"
    )
    return (
        "تم تسجيل تفضيلاتك:\n"
        f"• الفئة الأساسية: {state.get('preferred_category', '—')}\n"
        f"• العدد: {state.get('quantity', '—')}\n"
        f"• المنطقة/الطبقة: {state.get('preferred_area', '—')}\n"
        f"• مقاعد متجاورة: {'نعم' if state.get('adjacent') else 'لا'}\n"
        f"• البديل: {fallback_text}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = _reply_target(update)
    if not _allowed(update):
        await msg.reply_text(
            "البوت غير مفعّل لهذا الحساب. ابعت /id لمعرفة رقم المحادثة، "
            "ثم أضفه إلى TELEGRAM_CHAT_ID في ملف .env وأعد تشغيل البوت."
        )
        return
    chat_id = update.effective_chat.id
    state = _user_state(chat_id)
    state.setdefault("event_url", settings.event_url)
    state.setdefault("event_name", settings.event_name)
    _set_user_state(chat_id, state)
    await msg.reply_text(
        "أهلاً بيك في مساعد حجز Webook 🎟️\n\n"
        f"الفعالية الحالية: {state['event_name']}\n{state['event_url']}\n\n"
        "ابعت رابط فعالية Webook لتغييره، أو اكتب /book لتجهيز طلبك.\n"
        "اكتب /help لعرض الأوامر."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    await _reply_target(update).reply_text(
        "الأوامر المتاحة:\n"
        "/id — معرفة رقم المحادثة لإعداد صلاحية البوت\n"
        "/start — بدء البوت وعرض الفعالية الحالية\n"
        "/book — تحديد الفئة والعدد والمنطقة وتفضيل التجاور\n"
        "/open — فتح الفعالية في متصفح ظاهر على جهاز تشغيل البوت\n"
        "/inspect — قراءة الفئات والأسعار الظاهرة في الصفحة المفتوحة\n"
        "/scan — فحص تلميحات المقاعد الظاهرة بالماوس دون اختيارها\n"
        "/map — إرسال صورة لخريطة المقاعد الظاهرة\n"
        "/status — عرض الفعالية وملخص الطلب\n"
        "/payment — تسجيل أنك وصلت لمرحلة الدفع\n"
        "/cancel — إلغاء إعداد الطلب\n\n"
        "تسجيل الدخول والـQueue واختيار المقاعد وتأكيد الطلب والدفع تتم بواسطتك على Webook.\n"
        "بعد الوصول لخريطة المقاعد، استخدم /map لصورة الخريطة أو /scan لفحص التلميحات الظاهرة."
    )


async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    chat_id = update.effective_chat.id
    state = _user_state(chat_id)
    _reset_booking_preferences(state)
    _set_user_state(chat_id, state)
    keyboard = [[InlineKeyboardButton(c, callback_data=f"cat:{c}")] for c in CATEGORIES]
    await _reply_target(update).reply_text(
        "اختار الفئة المفضلة. الاختيارات دي لتسجيل تفضيلك فقط؛ التوفر الفعلي هتراجعه على Webook:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _allowed(update):
        return
    chat_id = update.effective_chat.id
    state = _user_state(chat_id)
    data = query.data or ""
    if data.startswith("cat:") and state.get("step") == "category":
        category = data.split(":", 1)[1]
        if category not in CATEGORIES:
            return
        state.update(preferred_category=category, step="quantity")
        _set_user_state(chat_id, state)
        keyboard = [[InlineKeyboardButton(str(n), callback_data=f"qty:{n}") for n in (1, 2, 3)]]
        await query.edit_message_text(f"الفئة المفضلة: {category}\nاختار عدد التذاكر:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("qty:") and state.get("step") == "quantity":
        try:
            quantity = int(data.split(":", 1)[1])
        except ValueError:
            return
        if quantity not in (1, 2, 3):
            return
        state.update(quantity=quantity, step="adjacent")
        _set_user_state(chat_id, state)
        keyboard = [[
            InlineKeyboardButton("لازم جنب بعض", callback_data="adj:yes"),
            InlineKeyboardButton("مش شرط", callback_data="adj:no"),
        ]]
        await query.edit_message_text("هل المقاعد لازم تكون جنب بعض؟", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("adj:") and state.get("step") == "adjacent":
        state.update(adjacent=(data == "adj:yes"), step="region")
        _set_user_state(chat_id, state)
        await query.edit_message_text("اكتب المنطقة أو الطبقة المفضلة (مثال: Layer 2 أو Bronze 2).")
    elif data.startswith("fallback:") and state.get("step") == "fallback_approval":
        approved = data == "fallback:yes"
        state.update(fallback_approved=approved, step="ready")
        _set_user_state(chat_id, state)
        await query.edit_message_text(
            _preferences_summary(state)
            + ("\nالبديل Silver مسموح بموافقتك فقط." if approved else "\nلن يتم استخدام Silver؛ Bronze فقط.")
            + "\n\nاستخدم /open لفتح الفعالية."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    msg = _reply_target(update)
    text = (msg.text or "").strip()
    chat_id = update.effective_chat.id
    state = _user_state(chat_id)

    if state.get("step") == "region" and "webook.com" not in text.lower():
        if not text or len(text) > 100:
            await msg.reply_text("اكتب اسم المنطقة أو الطبقة في 100 حرف أو أقل.")
            return
        state.update(preferred_area=text)
        can_offer_fallback = (
            state.get("preferred_category") == "Bronze"
            and state.get("quantity") == 2
            and state.get("adjacent") is True
        )
        state["fallback_category"] = "Silver" if can_offer_fallback else None
        state["step"] = "fallback_approval" if can_offer_fallback else "ready"
        _set_user_state(chat_id, state)
        if state["fallback_category"]:
            keyboard = [[
                InlineKeyboardButton("أوافق على Silver لو Bronze مش متاح", callback_data="fallback:yes"),
                InlineKeyboardButton("Bronze فقط", callback_data="fallback:no"),
            ]]
            await msg.reply_text(
                "هل توافق على Silver كبديل فقط لو لم يتوفر زوج Bronze متجاور؟\n"
                "لن يتم اعتماد Silver بدون موافقتك.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await msg.reply_text(_preferences_summary(state) + "\n\nاستخدم /open لفتح الفعالية.")
        return

    if "webook.com" not in text.lower():
        await msg.reply_text("ابعت رابط فعالية Webook كامل، أو استخدم /book لتجهيز طلبك.")
        return
    try:
        validate_event_url(text)
    except ValueError as exc:
        await msg.reply_text(str(exc))
        return
    parsed = urlparse(text)
    if "/events/" not in parsed.path.lower():
        await msg.reply_text("الرابط لازم يكون رابط فعالية ويحتوي على /events/.")
        return
    # A new event invalidates the previous event-specific preferences.
    state = {
        "event_url": text,
        "event_name": _event_name(text),
        "handoff_reported_by_user": False,
    }
    _set_user_state(chat_id, state)
    await msg.reply_text(
        f"تم تغيير الفعالية النشطة إلى:\n{state['event_name']}\n{text}\n\n"
        "اتمسحت تفضيلات الفعالية السابقة. استخدم /book لتجهيز طلب جديد."
    )


async def open_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    msg = _reply_target(update)
    state = _user_state(update.effective_chat.id)
    url = state.get("event_url", settings.event_url)
    await msg.reply_text("بفتح صفحة الفعالية في متصفح ظاهر على جهاز تشغيل البوت. سجّل دخولك وتعامل مع الـQueue بنفسك.")
    try:
        opened = await asyncio.get_running_loop().run_in_executor(_BROWSER_EXECUTOR, open_event_page, url)
    except Exception as exc:
        log.exception("Browser launch failed")
        await msg.reply_text(f"تعذر فتح المتصفح ({type(exc).__name__}). تأكد من تثبيت Chromium.")
        return
    if opened:
        await msg.reply_text("الصفحة اتفتحت. بعد تسجيل الدخول وإنهاء أي Queue بنفسك، استخدم /inspect لقراءة الفئات والأسعار الظاهرة.")
    else:
        await msg.reply_text("لم أتمكن من تشغيل Chromium. نفّذ من Terminal: .venv\\Scripts\\python.exe -m playwright install chromium")


async def inspect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    msg = _reply_target(update)
    try:
        result = await asyncio.get_running_loop().run_in_executor(_BROWSER_EXECUTOR, inspect_visible_event_page)
    except Exception as exc:
        await msg.reply_text(f"مش قادر أقرأ الصفحة الظاهرة: {exc}\nافتح صفحة الفعالية أولاً باستخدام /open.")
        return
    if result.categories:
        lines = [f"• {item.name}: {item.price_display}" for item in result.categories]
        message = "الفئات والأسعار الظاهرة حاليًا:\n" + "\n".join(lines)
    else:
        message = "لم أجد فئات وأسعار واضحة في النص الظاهر. راجع الصفحة يدويًا."
    if result.availability_evidence:
        message += "\nعبارات حالة ظهرت بالنص: " + ", ".join(result.availability_evidence)
    message += "\n\nظهور الفئة والسعر لا يؤكد وجود مقاعد متاحة أو متجاورة. اختار المقاعد بنفسك على الخريطة."
    await msg.reply_text(message)

async def scan_seats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze visible seat tooltips without clicking or selecting seats."""
    if not _allowed(update):
        return

    msg = _reply_target(update)
    chat_id = update.effective_chat.id
    state = _user_state(chat_id)

    category = state.get("preferred_category")
    quantity = state.get("quantity")
    adjacent = state.get("adjacent", False)

    if not category or not quantity:
        await msg.reply_text("جهّز طلبك الأول باستخدام /book.")
        return

    await msg.reply_text(
        "بفحص التلميحات الظاهرة بحركة الماوس فقط. "
        "لن يتم الضغط على أي مقعد أو اختياره."
    )

    try:
        observations = await asyncio.get_running_loop().run_in_executor(
            _BROWSER_EXECUTOR, scan_visible_seat_map
        )
    except Exception as exc:
        await msg.reply_text(f"تعذر فحص الخريطة: {exc}")
        return

    if not observations:
        await msg.reply_text(
            "لم أجد تلميحات مقاعد نصية واضحة. "
            "راجع الخريطة يدويًا أو استخدم /map لعرض صورتها."
        )
        return

    seats = [
        seat
        for item in observations
        if (seat := parse_visible_seat_tooltip(item.text)) is not None
    ]

    if not seats:
        await msg.reply_text(
            "لم أجد مقاعد تتضمن رقم الصف ورقم المقعد وحالة توفر صريحة. "
            "النصوص الظاهرة وحدها لا تكفي لتأكيد التوفر."
        )
        return

    def matching_seats(target_category):
        return [
            seat for seat in seats
            if seat.category
            and seat.category.casefold() == target_category.casefold()
        ]

    if quantity == 1:
        matches = matching_seats(category)
        if not matches:
            await msg.reply_text(
                f"لم أجد مقاعد {category} متاحة ببيانات واضحة. "
                "راجع الخريطة بنفسك."
            )
            return

        lines = [
            f"• صف {seat.row} - مقعد {seat.number} ({seat.category})"
            for seat in matches[:20]
        ]
        await msg.reply_text(
            f"مقاعد {category} التي ظهرت كمتاحة في النصوص:\n"
            + "\n".join(lines)
            + "\n\nدي نتائج قراءة أولية وليست تأكيدًا للحجز."
        )
        return

    if quantity == 2 and not adjacent:
        matches = matching_seats(category)
        if not matches:
            await msg.reply_text(
                f"لم أجد مقاعد {category} متاحة ببيانات واضحة. راجع الخريطة بنفسك."
            )
            return
        lines = [
            f"• صف {seat.row} - مقعد {seat.number} ({seat.category})"
            for seat in matches[:20]
        ]
        await msg.reply_text(
            f"مقاعد {category} الفردية التي ظهرت كمتاحة (من غير اشتراط التجاور):\n"
            + "\n".join(lines)
            + "\n\nدي نتائج قراءة أولية؛ اختار مقعدين بنفسك وتأكد من التوفر على Webook."
        )
        return

    if adjacent and quantity == 2:
        pairs = find_adjacent_visible_pairs(observations, category=category)

        if not pairs and category == "Bronze" and state.get("fallback_approved"):
            pairs = find_adjacent_visible_pairs(
                observations, category="Silver"
            )
            if pairs:
                category = "Silver"

        if not pairs:
            await msg.reply_text(
                f"لم أجد زوجًا مرشحًا من مقعدين متتاليين في صف واحد "
                f"ضمن فئة {category}."
                "\nلم أستخدم فئة بديلة بدون موافقتك، ولم يتم اختيار أي مقعد."
            )
            return

        lines = [
            f"• صف {pair.first.row}: "
            f"مقعد {pair.first.number} و{pair.second.number} "
            f"({category})"
            for pair in pairs[:15]
        ]
        await msg.reply_text(
            "أزواج مقاعد مرشحة للمراجعة البصرية:\n"
            + "\n".join(lines)
            + "\n\nتتابع أرقام المقاعد لا يثبت التجاور الفعلي؛ "
            "تأكد من الخريطة بنفسك قبل الاختيار."
        )
        return

    if quantity >= 3:
        await msg.reply_text(
            "الفحص الحالي لا يدعم ترشيح مجموعات من 3 مقاعد أو أكثر. "
            "استخدم صورة /map وراجع المقاعد يدويًا على Webook؛ لم يتم اختيار أي مقعد."
        )
        return

    await msg.reply_text("عدد التذاكر أو تفضيل التجاور غير واضح. أعد إعداد الطلب باستخدام /book.")
async def seat_map_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a screenshot of the currently visible seat-map canvas."""
    if not _allowed(update):
        return
    msg = _reply_target(update)
    with tempfile.TemporaryDirectory(prefix="webook-map-") as temp_dir:
        image_path = os.path.join(temp_dir, "visible-seat-map.png")
        try:
            await asyncio.get_running_loop().run_in_executor(
                _BROWSER_EXECUTOR, capture_seat_map_screenshot, image_path
            )
            with open(image_path, "rb") as image_file:
                await msg.reply_photo(
                    photo=image_file,
                    caption=(
                        "صورة من خريطة المقاعد الظاهرة حاليًا.\n"
                        "الصورة للمراجعة فقط؛ لم يتم اختيار أي مقعد، ولا تثبت التوفر أو التجاور."
                    ),
                )
        except Exception as exc:
            await msg.reply_text(f"تعذر التقاط صورة الخريطة: {exc}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    state = _user_state(update.effective_chat.id)
    await _reply_target(update).reply_text(
        f"الفعالية: {state.get('event_name', settings.event_name)}\n"
        f"الرابط: {state.get('event_url', settings.event_url)}\n"
        f"الفئة: {state.get('preferred_category', 'لم تُحدد')}\n"
        f"العدد: {state.get('quantity', '—')}\n"
        f"المنطقة: {state.get('preferred_area', 'لم تُحدد')}\n"
        f"مقاعد متجاورة: {'نعم' if state.get('adjacent') else 'لا/لم يُحدد'}\n"
        f"بديل Silver: {'موافق عليه' if state.get('fallback_approved') else 'غير مسموح/لم يُحدد'}\n"
        f"وصلت للدفع حسب إفادتك: {'نعم' if state.get('handoff_reported_by_user') else 'لا'}"
    )


async def payment_handoff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    state = _user_state(update.effective_chat.id)
    state["handoff_reported_by_user"] = True
    state["handoff_stage"] = "payment_review_by_customer"
    _set_user_state(update.effective_chat.id, state)
    await _reply_target(update).reply_text(
        "سجّلت إنك وصلت لمرحلة الدفع. راجع اسم الفعالية وعدد التذاكر والمقاعد والسعر بنفسك، "
        "وأكمل الدفع على Webook إذا كانت التفاصيل صحيحة. الوصول لصفحة الدفع لا يعني تأكيد الحجز."
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    chat_id = update.effective_chat.id
    state = _user_state(chat_id)
    for key in ("step", "preferred_category", "fallback_category", "fallback_approved", "quantity", "adjacent", "preferred_area"):
        state.pop(key, None)
    _set_user_state(chat_id, state)
    await _reply_target(update).reply_text("تم إلغاء إعداد الطلب. رابط الفعالية الحالي لم يتغير.")


async def show_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Expose only the caller's own chat ID so the owner can configure the allowlist."""
    chat = update.effective_chat
    if chat is None:
        return
    await _reply_target(update).reply_text(
        f"رقم المحادثة (Chat ID): {chat.id}\n"
        "انسخ الرقم إلى TELEGRAM_CHAT_ID في ملف .env ثم أعد تشغيل البوت."
    )


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN غير موجود. ضعه في ملف .env ثم أعد التشغيل.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("id", show_chat_id))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("book", book))
    app.add_handler(CommandHandler("open", open_event))
    app.add_handler(CommandHandler("inspect", inspect))
    app.add_handler(CommandHandler("scan", scan_seats))
    app.add_handler(CommandHandler("map", seat_map_photo))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("payment", payment_handoff))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    if not os.getenv("TELEGRAM_CHAT_ID", "").strip():
        log.warning(
            "TELEGRAM_CHAT_ID is empty. The bot is locked: only /id is available until an allowlist is configured."
        )
    log.info("Webook Telegram assistant starting")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    main()

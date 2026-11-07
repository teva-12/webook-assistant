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
    inspect_visible_event_page, open_event_page, scan_visible_seat_map, validate_event_url,
)
from app.core.config import settings  # noqa: E402

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


def _allowed(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    allowed_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return not allowed_id or str(chat.id) == allowed_id


def _event_name(url: str) -> str:
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    # Remove common trailing numeric Webook identifiers from the display label.
    slug = __import__("re").sub(r"-\d+$", "", slug)
    return slug.replace("-", " ").title() or "Webook Event"


def _reply_target(update: Update):
    return update.effective_message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = _reply_target(update)
    if not _allowed(update):
        await msg.reply_text("البوت غير مفعّل لهذا الحساب.")
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
        "/start — بدء البوت وعرض الفعالية الحالية\n"
        "/book — تحديد الفئة والعدد والمنطقة وتفضيل التجاور\n"
        "/open — فتح الفعالية في متصفح ظاهر على جهاز تشغيل البوت\n"
        "/inspect — قراءة الفئات والأسعار الظاهرة في الصفحة المفتوحة\n"
        "/scan — فحص تلميحات المقاعد الظاهرة بالماوس دون اختيارها\n"
        "/status — عرض الفعالية وملخص الطلب\n"
        "/payment — تسجيل أنك وصلت لمرحلة الدفع\n"
        "/cancel — إلغاء إعداد الطلب\n\n"
        "تسجيل الدخول والـQueue واختيار المقاعد وتأكيد الطلب والدفع تتم بواسطتك على Webook.\n"
        "بعد الوصول لخريطة المقاعد، استخدم /scan لفحص بيانات المقاعد التي تظهر عند تحريك الماوس."
    )


async def book(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    chat_id = update.effective_chat.id
    state = _user_state(chat_id)
    state["step"] = "category"
    state["handoff_reported_by_user"] = False
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
        state.update(preferred_area=text, step="ready")
        state["fallback_category"] = "Silver" if state.get("preferred_category") != "Silver" else "Gold"
        _set_user_state(chat_id, state)
        await msg.reply_text(
            "تم تسجيل تفضيلاتك:\n"
            f"• الفئة: {state['preferred_category']}\n"
            f"• العدد: {state['quantity']}\n"
            f"• المنطقة/الطبقة: {text}\n"
            f"• مقاعد متجاورة: {'نعم' if state['adjacent'] else 'لا'}\n\n"
            "استخدم /open لفتح الفعالية على جهاز تشغيل البوت. والبديل المقترح "
            f"{state['fallback_category']} لا يتم اختياره إلا بموافقتك."
        )
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
    """Collect visible seat tooltip text by hover only; never click/select seats."""
    if not _allowed(update):
        return
    msg = _reply_target(update)
    await msg.reply_text(
        "بفحص خريطة المقاعد بحركة الماوس فقط. الفحص لا يختار أي كرسي. "
        "تأكد إنك فتحت الخريطة واخترت Layer 2 وكبّرت الجزء المطلوب قبل الفحص."
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
            "لم ألتقط تلميحات مقاعد نصية من المرور بالماوس. قد تكون بيانات المقعد مرسومة داخل Canvas فقط. "
            "لم يتم الضغط على أي مقعد."
        )
        return
    lines = [f"• {item.text} (موضع تقريبي: {round(item.x)}, {round(item.y)})" for item in observations[:30]]
    await msg.reply_text(
        "النصوص التي ظهرت أثناء المرور بالماوس (من غير اختيار):\n" + "\n".join(lines)
        + "\n\nدي مرحلة معايرة أولية؛ مش هاعتبر أي مقعد متاح أو متجاور إلا لما تظهر بياناته بوضوح."
    )


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
    for key in ("step", "preferred_category", "fallback_category", "quantity", "adjacent", "preferred_area"):
        state.pop(key, None)
    _set_user_state(chat_id, state)
    await _reply_target(update).reply_text("تم إلغاء إعداد الطلب. رابط الفعالية الحالي لم يتغير.")


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN غير موجود. ضعه في ملف .env ثم أعد التشغيل.")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("book", book))
    app.add_handler(CommandHandler("open", open_event))
    app.add_handler(CommandHandler("inspect", inspect))
    app.add_handler(CommandHandler("scan", scan_seats))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("payment", payment_handoff))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    log.info("Webook Telegram assistant starting")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    main()

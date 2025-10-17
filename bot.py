#!/usr/bin/env python3
# bot.py
import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List

from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ludic-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_HOST = os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))

if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN не задан")
    raise SystemExit("TELEGRAM_TOKEN required")
if not API_FOOTBALL_KEY:
    logger.error("API_FOOTBALL_KEY не задан")
    raise SystemExit("API_FOOTBALL_KEY required")

BASE_URL = f"https://{API_FOOTBALL_HOST}"
HEADERS = {
    "x-rapidapi-host": API_FOOTBALL_HOST,
    "x-rapidapi-key": API_FOOTBALL_KEY,
    "Accept": "application/json",
}

def isoformat_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def fetch_fixtures(from_iso: str, to_iso: str) -> List[dict]:
    url = f"{BASE_URL}/fixtures"
    params = {"from": from_iso, "to": to_iso}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=API_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", [])
    except Exception as e:
        logger.exception("Ошибка fetch_fixtures: %s", e)
        return []

def format_match_item(f: dict) -> str:
    try:
        fixture = f.get("fixture", {})
        teams = f.get("teams", {})
        league = f.get("league", {}).get("name") or f.get("league", {})
        date_raw = fixture.get("date")
        if date_raw:
            dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
            when = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        else:
            when = "unknown time"
        home = teams.get("home", {}).get("name", "Home")
        away = teams.get("away", {}).get("name", "Away")
        return f"{when} — {home} vs {away} ({league})"
    except Exception:
        return str(f)

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Отправь /matches чтобы увидеть матчи, которые начнутся в ближайший час.")

def matches_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    bot: Bot = context.bot
    now = datetime.now(timezone.utc)
    to = now + timedelta(hours=1)
    from_iso = isoformat_z(now)
    to_iso = isoformat_z(to)
    bot.send_message(chat_id=chat_id, text=f"Ищу матчи с {from_iso} по {to_iso} ...")
    fixtures = fetch_fixtures(from_iso, to_iso)
    if not fixtures:
        bot.send_message(chat_id=chat_id, text="Матчи в ближайший час не найдены.")
        return
    lines = [format_match_item(f) for f in fixtures]
    bot.send_message(chat_id=chat_id, text="\n".join(lines[:30]))

def text_handler(update: Update, context: CallbackContext):
    txt = update.message.text.strip().lower()
    if txt in ("matches", "матчи", "матч", "next"):
        matches_command(update, context)
    else:
        update.message.reply_text("Я понимаю /matches. Отправь /matches или напиши 'matches'.")

def error_handler(update: Update, context: CallbackContext):
    logger.error("Update caused error: %s", context.error)

def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("matches", matches_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
    dp.add_error_handler(error_handler)
    logger.info("Бот запущен, polling...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

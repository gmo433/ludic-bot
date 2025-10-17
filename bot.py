#!/usr/bin/env python3
import os
import logging
import requests
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ludic-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_HOST = os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io")
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))

if not TELEGRAM_TOKEN or not API_FOOTBALL_KEY:
    raise SystemExit("TELEGRAM_TOKEN and API_FOOTBALL_KEY are required")

BASE_URL = f"https://{API_FOOTBALL_HOST}"
HEADERS = {
    "x-rapidapi-host": API_FOOTBALL_HOST,
    "x-rapidapi-key": API_FOOTBALL_KEY,
    "Accept": "application/json",
}

def isoformat_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

async def fetch_fixtures(from_iso: str, to_iso: str):
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
    fixture = f.get("fixture", {})
    teams = f.get("teams", {})
    league = f.get("league", {}).get("name") or f.get("league", {})
    date_raw = fixture.get("date")
    dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00")) if date_raw else None
    when = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if dt else "unknown time"
    home = teams.get("home", {}).get("name", "Home")
    away = teams.get("away", {}).get("name", "Away")
    return f"{when} — {home} vs {away} ({league})"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь /matches чтобы увидеть матчи, которые начнутся в ближайший час."
    )

async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    now = datetime.now(timezone.utc)
    to = now + timedelta(hours=1)
    from_iso = isoformat_z(now)
    to_iso = isoformat_z(to)
    await context.bot.send_message(chat_id=chat_id, text=f"Ищу матчи с {from_iso} по {to_iso} ...")
    fixtures = await fetch_fixtures(from_iso, to_iso)
    if not fixtures:
        await context.bot.send_message(chat_id=chat_id, text="Матчи в ближайший час не найдены.")
        return
    lines = [format_match_item(f) for f in fixtures]
    await context.bot.send_message(chat_id=chat_id, text="\n".join(lines[:30]))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip().lower()
    if txt in ("matches", "матчи", "матч", "next"):
        await matches_command(update, context)
    else:
        await update.message.reply_text("Я понимаю /matches. Отправь /matches или напиши 'matches'.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("matches", matches_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Бот запущен, polling...")
    app.run_polling()

if __name__ == "__main__":
    main()

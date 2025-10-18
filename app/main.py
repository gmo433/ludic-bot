import os
import logging
import threading
import asyncio
from datetime import datetime, timedelta

import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- ENVIRONMENT VARIABLES ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_SPORT_KEY = os.getenv("API_SPORT_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
if not API_SPORT_KEY:
    raise RuntimeError("API_SPORT_KEY is required")

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# --- WEB APP STATIC FILES ---
@app.get("/")
def index():
    return FileResponse("app/webapp/index.html")

@app.get("/style.css")
def style():
    return FileResponse("app/webapp/style.css")

@app.get("/app.js")
def app_js():
    return FileResponse("app/webapp/app.js")

# --- API ENDPOINT FOR MATCHES ---
@app.get("/api/matches")
def api_matches():
    try:
        now = datetime.utcnow()
        to = now + timedelta(hours=2)
        params = {
            "from": now.strftime("%Y-%m-%d %H:%M:%S"),
            "to": to.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "UTC"
        }
        headers = {"X-API-KEY": API_SPORT_KEY}
        url = "https://app.api-sport.ru/api/football/matches"
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return JSONResponse(content=resp.json())
    except Exception as e:
        log.exception("Error fetching matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- TELEGRAM HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(
        text="⚽ Открыть мини-приложение",
        web_app=types.WebAppInfo(url=os.getenv("WEBAPP_URL", "https://<YOUR_PUBLIC_URL>/"))
    )
    await message.answer(
        "Привет! 👋\nНажми кнопку ниже, чтобы открыть мини-приложение с ближайшими матчами:",
        reply_markup=kb.as_markup()
    )

@dp.message(Command("matches"))
async def cmd_matches(message: types.Message):
    await message.answer("⏳ Загружаю ближайшие матчи...")
    try:
        resp = requests.get(os.getenv("WEBAPP_API_INTERNAL", "http://127.0.0.1:8080/api/matches"), timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            await message.answer("⚽ Нет матчей в ближайшие 2 часа.")
            return
        for m in data:
            league = m.get("league", {}).get("name", "—")
            home = m.get("teams", {}).get("home", {}).get("name", "Home")
            away = m.get("teams", {}).get("away", {}).get("name", "Away")
            time = m.get("time", "—")
            text = f"🏆 <b>{league}</b>\n⚽ {home} vs {away}\n🕒 {time}"
            await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении матчей: {e}")

# --- THREADS: BOT + API ---
def run_bot():
    asyncio.run(dp.start_polling(bot))

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    t_api = threading.Thread(target=run_api, daemon=True)
    t_api.start()
    log.info("FastAPI started on port 8080")
    run_bot()

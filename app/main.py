import os
import logging
import threading
import asyncio
from datetime import datetime, timedelta
import hmac
import hashlib
import json

import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- ENVIRONMENT VARIABLES ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_SPORT_KEY = os.getenv("API_SPORT_KEY")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()

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

# --- INITDATA VALIDATION ---
def validate_init_data(init_data: str) -> bool:
    """Validate Telegram Web App initData"""
    try:
        pairs = init_data.split('&')
        data_dict = {}
        hash_value = None
        
        for pair in pairs:
            key, value = pair.split('=', 1)
            if key == 'hash':
                hash_value = value
            else:
                data_dict[key] = value
        
        if not hash_value:
            return False
        
        check_string = '\n'.join([f"{k}={data_dict[k]}" for k in sorted(data_dict.keys())])
        
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=TELEGRAM_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        calculated_hash = hmac.new(
            key=secret_key,
            msg=check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == hash_value
    except Exception as e:
        log.error(f"Error validating initData: {e}")
        return False

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

# --- API ENDPOINTS ---
@app.get("/api/matches")
def api_matches(request: Request):
    """Endpoint for Mini App with initData validation"""
    try:
        # Get initData from header
        init_data = request.headers.get("X-Telegram-Init-Data")
        
        if not init_data:
            return JSONResponse(
                status_code=401,
                content={"error": "initData required"}
            )
        
        # Validate initData
        if not validate_init_data(init_data):
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid initData"}
            )
        
        return get_matches_data()
        
    except Exception as e:
        log.exception("Error fetching matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches")
def api_internal_matches():
    """Internal endpoint for bot commands without initData validation"""
    try:
        return get_matches_data()
    except Exception as e:
        log.exception("Error fetching matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

def get_matches_data():
    """Common function to fetch matches data with proper API key header"""
    try:
        now = datetime.utcnow()
        to = now + timedelta(hours=2)
        params = {
            "from": now.strftime("%Y-%m-%d %H:%M:%S"),
            "to": to.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "UTC"
        }
        
        # ✅ ПРАВИЛЬНАЯ ПЕРЕДАЧА КЛЮЧА В ЗАГОЛОВКЕ
        headers = {
            "X-API-KEY": API_SPORT_KEY  # Ключ передается в заголовке
        }
        
        url = "https://app.api-sport.ru/api/football/matches"
        
        log.info(f"Making request to: {url}")
        log.info(f"With headers: { {k: '***' if k == 'X-API-KEY' else v for k, v in headers.items()} }")
        log.info(f"With params: {params}")
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        log.info(f"Response status: {resp.status_code}")
        
        # Если ошибка 401 - проблема с ключом
        if resp.status_code == 401:
            return JSONResponse(
                status_code=401,
                content={"error": "API key invalid or unauthorized"}
            )
        
        resp.raise_for_status()
        data = resp.json()
        
        log.info(f"Received {len(data.get('data', []))} matches")
        
        return JSONResponse(content=data)
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            log.error("API key is invalid or expired")
            return JSONResponse(
                status_code=401,
                content={"error": "API key authentication failed"}
            )
        raise e
    except Exception as e:
        log.exception("Error in get_matches_data")
        raise e

# --- TELEGRAM HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    # Всегда показываем кнопки
    kb.button(text="📅 Получить матчи", callback_data="get_matches")
    kb.button(text="🔄 Обновить", callback_data="get_matches") 
    kb.button(text="ℹ️ Помощь", callback_data="help")
    kb.adjust(2, 1)
    
    await message.answer(
        "Привет! 👋\nЯ бот для просмотра футбольных матчей.\n\n"
        "⚽ *Доступные команды:*\n"
        "/matches - Показать ближайшие матчи\n"
        "/start - Перезапустить бота\n\n"
        "Используйте кнопки ниже:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("matches"))
async def cmd_matches(message: types.Message):
    await message.answer("⏳ Загружаю ближайшие матчи...")
    try:
        # Используем внутренний endpoint
        internal_url = "http://127.0.0.1:8080/api/internal/matches"
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            error_data = resp.json()
            await message.answer(f"❌ Ошибка API: {error_data.get('error', 'Unknown error')}")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await message.answer("⚽ Нет матчей в ближайшие 2 часа.")
            return
            
        for m in data[:5]:
            league = m.get("league", {}).get("name", "—")
            home = m.get("teams", {}).get("home", {}).get("name", "Home")
            away = m.get("teams", {}).get("away", {}).get("name", "Away")
            time = m.get("time", "—")
            text = f"🏆 <b>{league}</b>\n⚽ {home} vs {away}\n🕒 {time}"
            await message.answer(text, parse_mode="HTML")
            
        if len(data) > 5:
            await message.answer(f"📊 Показано 5 из {len(data)} матчей")
            
    except Exception as e:
        log.error(f"Error in cmd_matches: {e}")
        await message.answer(f"❌ Ошибка при получении матчей: {e}")

@dp.callback_query(lambda c: c.data == "get_matches")
async def process_callback(callback: types.CallbackQuery):
    await callback.answer("⏳ Загружаю матчи...")
    await cmd_matches(callback.message)

@dp.callback_query(lambda c: c.data == "help")
async def process_help(callback: types.CallbackQuery):
    await callback.message.answer(
        "🤖 *Ludic Bot Help*\n\n"
        "⚽ *Команды:*\n"
        "/start - Начать работу\n" 
        "/matches - Показать ближайшие матчи\n\n"
        "📊 *Функциональность:*\n"
        "- Просмотр футбольных матчей\n"
        "- Ближайшие 2 часа\n"
        "- Разные лиги и турниры",
        parse_mode="Markdown"
    )
    await callback.answer()

# --- THREADS: BOT + API ---
def run_bot():
    asyncio.run(dp.start_polling(bot))

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    log.info("Starting bot with proper API key headers")
    t_api = threading.Thread(target=run_api, daemon=True)
    t_api.start()
    log.info("FastAPI started on port 8080")
    run_bot()

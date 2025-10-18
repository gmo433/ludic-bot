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
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

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
    """
    Validate Telegram Web App initData
    Docs: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    try:
        # Parse initData
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
        
        # Create data check string
        check_string = '\n'.join([f"{k}={data_dict[k]}" for k in sorted(data_dict.keys())])
        
        # Calculate secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=TELEGRAM_BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        # Calculate HMAC
        calculated_hash = hmac.new(
            key=secret_key,
            msg=check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == hash_value
    except Exception as e:
        log.error(f"Error validating initData: {e}")
        return False

def parse_init_data(init_data: str) -> dict:
    """Parse initData and return user data"""
    try:
        pairs = init_data.split('&')
        user_data = {}
        
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                if key != 'hash':
                    # URL decode the value
                    value = requests.utils.unquote(value)
                    # Try to parse JSON for user object
                    if key == 'user':
                        user_data[key] = json.loads(value)
                    else:
                        user_data[key] = value
        
        return user_data
    except Exception as e:
        log.error(f"Error parsing initData: {e}")
        return {}

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

# --- PROTECTED API ENDPOINTS ---
@app.get("/api/matches")
def api_matches(request: Request):
    """Protected endpoint that requires initData validation"""
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
        
        # Parse user data (optional)
        user_data = parse_init_data(init_data)
        log.info(f"Request from user: {user_data.get('user', {}).get('username', 'unknown')}")
        
        # Your existing matches logic
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

@app.get("/api/user")
def api_user(request: Request):
    """Get user data from initData"""
    init_data = request.headers.get("X-Telegram-Init-Data")
    
    if not init_data:
        return JSONResponse(
            status_code=401,
            content={"error": "initData required"}
        )
    
    if not validate_init_data(init_data):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid initData"}
        )
    
    user_data = parse_init_data(init_data)
    return JSONResponse(content={"user": user_data})

# --- TELEGRAM HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    if WEBAPP_URL:
        kb.button(
            text="⚽ Открыть мини-приложение",
            web_app=types.WebAppInfo(url=WEBAPP_URL)
        )
    
    await message.answer(
        "Привет! 👋\nНажми кнопку ниже, чтобы открыть мини-приложение с ближайшими матчами:",
        reply_markup=kb.as_markup()
    )

@dp.message(Command("matches"))
async def cmd_matches(message: types.Message):
    await message.answer("⏳ Загружаю ближайшие матчи...")
    try:
        # For bot commands, we don't need initData validation
        internal_url = os.getenv("WEBAPP_API_INTERNAL", "http://127.0.0.1:8080/api/matches")
        resp = requests.get(internal_url, timeout=10)
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

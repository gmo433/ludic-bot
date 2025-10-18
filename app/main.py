# Создаем файл с обновленным кодом
cat > main.py << 'EOF'
import os
import logging
import threading
import asyncio
from datetime import datetime, timedelta
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_SPORT_KEY = os.getenv("API_SPORT_KEY")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()

if not TELEGRAM_BOT_TOKEN or not API_SPORT_KEY:
    raise RuntimeError("Missing required environment variables")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

@app.get("/")
def index(): return FileResponse("app/webapp/index.html")
@app.get("/style.css") 
def style(): return FileResponse("app/webapp/style.css")
@app.get("/app.js")
def app_js(): return FileResponse("app/webapp/app.js")

@app.get("/api/matches")
def api_matches():
    try:
        now = datetime.utcnow()
        to = now + timedelta(hours=2)
        params = {"from": now.strftime("%Y-%m-%d %H:%M:%S"), "to": to.strftime("%Y-%m-%d %H:%M:%S"), "timezone": "UTC"}
        headers = {"X-API-KEY": API_SPORT_KEY}
        resp = requests.get("https://app.api-sport.ru/api/football/matches", headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return JSONResponse(content=resp.json())
    except Exception as e:
        log.exception("Error fetching matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    log.info(f"WEBAPP_URL value: '{WEBAPP_URL}'")
    
    # Всегда показываем кнопки, независимо от WEBAPP_URL
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
        resp = requests.get("http://127.0.0.1:8080/api/matches", timeout=10)
        resp.raise_for_status()
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
        await message.answer(f"❌ Ошибка при получении матчей: {e}")

@dp.callback_query(lambda c: c.data == "get_matches")
async def process_callback(callback: types.CallbackQuery):
    await cmd_matches(callback.message)
    await callback.answer()

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

def run_bot():
    asyncio.run(dp.start_polling(bot))

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    log.info("Starting bot with updated code - buttons should work!")
    t_api = threading.Thread(target=run_api, daemon=True)
    t_api.start()
    log.info("FastAPI started on port 8080")
    run_bot()
EOF

# Создаем ConfigMap
kubectl create configmap ludic-bot-code --from-file=main.py --dry-run=client -o yaml | kubectl apply -f -

# Обновляем deployment для использования ConfigMap
kubectl patch deployment ludic-bot -p '{"spec":{"template":{"spec":{"volumes":[{"name":"code-volume","configMap":{"name":"ludic-bot-code"}}],"containers":[{"name":"ludic-bot","volumeMounts":[{"name":"code-volume","mountPath":"/app/main.py","subPath":"main.py"}]}]}}}}'

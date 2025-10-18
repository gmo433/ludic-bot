import os
import logging
import threading
import asyncio
from datetime import datetime, timedelta
import hmac
import hashlib
import json

import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_SPORT_KEY = os.getenv("API_SPORT_KEY")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN обязателен")
if not API_SPORT_KEY:
    raise RuntimeError("API_SPORT_KEY обязателен")

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

# --- ПРОВЕРКА INITDATA ---
def validate_init_data(init_data: str) -> bool:
    """Проверка Telegram Web App initData"""
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
        log.error(f"Ошибка проверки initData: {e}")
        return False

# --- СТАТИЧЕСКИЕ ФАЙЛЫ WEB APP ---
@app.get("/")
def index():
    return FileResponse("app/webapp/index.html")

@app.get("/style.css")
def style():
    return FileResponse("app/webapp/style.css")

@app.get("/app.js")
def app_js():
    return FileResponse("app/webapp/app.js")

# --- ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ О МАТЧАХ ---
def get_matches_data():
    """Общая функция для получения данных о матчах"""
    try:
        # Получаем сегодняшнюю дату в правильном формате
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        # ✅ ПРАВИЛЬНЫЕ ПАРАМЕТРЫ СОГЛАСНО ДОКУМЕНТАЦИИ
        params = {
            "date": today  # Дата в формате YYYY-MM-DD
        }
        
        # ✅ ПРАВИЛЬНЫЕ ЗАГОЛОВКИ СОГЛАСНО ДОКУМЕНТАЦИИ
        headers = {
            "Authorization": API_SPORT_KEY  # Ключ передается в заголовке Authorization
        }
        
        # ✅ ПРАВИЛЬНЫЙ URL СОГЛАСНО ДОКУМЕНТАЦИИ
        url = "https://api.api-sport.ru/v1/football/matches"
        
        log.info(f"🔍 Отправляем запрос к API: {url}")
        log.info(f"📋 Параметры запроса: {params}")
        log.info(f"📋 Заголовки запроса: Authorization: ***")
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ОТВЕТА
        log.info(f"📡 Статус ответа: {resp.status_code}")
        log.info(f"📋 Заголовки ответа: {dict(resp.headers)}")
        
        # Логируем первые 500 символов ответа
        response_preview = resp.text[:500] + "..." if len(resp.text) > 500 else resp.text
        log.info(f"📄 Содержимое ответа: {response_preview}")
        
        # Проверяем, что ответ не пустой
        if not resp.text.strip():
            log.error("❌ Получен пустой ответ от API")
            return JSONResponse(
                status_code=500,
                content={"error": "Пустой ответ от API спортивных данных"}
            )
        
        # Проверяем статус код
        if resp.status_code == 401:
            log.error("❌ Ошибка 401: Неверный API ключ")
            return JSONResponse(
                status_code=401,
                content={"error": "Неверный API ключ"}
            )
        elif resp.status_code == 403:
            log.error("❌ Ошибка 403: Доступ запрещен")
            return JSONResponse(
                status_code=403,
                content={"error": "Доступ запрещен. Проверьте лимиты API"}
            )
        elif resp.status_code == 404:
            log.error("❌ Ошибка 404: API endpoint не найден")
            return JSONResponse(
                status_code=404,
                content={"error": "API endpoint не найден"}
            )
        elif resp.status_code != 200:
            log.error(f"❌ Ошибка HTTP {resp.status_code}")
            return JSONResponse(
                status_code=resp.status_code,
                content={"error": f"Ошибка API: {resp.status_code}"}
            )
        
        # Пытаемся разобрать JSON
        try:
            data = resp.json()
            
            # ✅ ПРАВИЛЬНАЯ СТРУКТУРА ДАННЫХ СОГЛАСНО ДОКУМЕНТАЦИИ
            matches = data.get("matches", [])
            total_matches = data.get("totalMatches", 0)
            
            log.info(f"✅ Успешно получено {total_matches} матчей")
            
            # Фильтруем матчи на ближайшие 2 часа
            now = datetime.utcnow()
            two_hours_later = now + timedelta(hours=2)
            
            filtered_matches = []
            for match in matches:
                start_timestamp = match.get("startTimestamp")
                if start_timestamp:
                    start_time = datetime.fromtimestamp(start_timestamp / 1000)
                    if now <= start_time <= two_hours_later:
                        filtered_matches.append(match)
            
            log.info(f"📊 После фильтрации осталось {len(filtered_matches)} матчей")
            
            return JSONResponse(content={
                "data": filtered_matches,
                "total": len(filtered_matches),
                "today_total": total_matches
            })
            
        except json.JSONDecodeError as e:
            log.error(f"❌ Ошибка разбора JSON: {e}")
            log.error(f"📄 Полное содержимое ответа: {resp.text}")
            return JSONResponse(
                status_code=500,
                content={"error": "Некорректный JSON от API"}
            )
            
    except requests.exceptions.Timeout:
        log.error("⏰ Таймаут запроса к API")
        return JSONResponse(
            status_code=504,
            content={"error": "Таймаут при запросе к API"}
        )
    except requests.exceptions.ConnectionError:
        log.error("🔌 Ошибка подключения к API")
        return JSONResponse(
            status_code=503,
            content={"error": "Ошибка подключения к API"}
        )
    except Exception as e:
        log.exception("💥 Неожиданная ошибка в get_matches_data")
        return JSONResponse(
            status_code=500,
            content={"error": f"Внутренняя ошибка: {str(e)}"}
        )

# --- API ENDPOINTS ---
@app.get("/api/matches")
def api_matches(request: Request):
    """Endpoint для Mini App с проверкой initData"""
    try:
        # Получаем initData из заголовка
        init_data = request.headers.get("X-Telegram-Init-Data")
        
        if not init_data:
            return JSONResponse(
                status_code=401,
                content={"error": "initData обязателен"}
            )
        
        # Проверяем initData
        if not validate_init_data(init_data):
            return JSONResponse(
                status_code=401,
                content={"error": "Неверный initData"}
            )
        
        return get_matches_data()
        
    except Exception as e:
        log.exception("Ошибка в api_matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches")
def api_internal_matches():
    """Внутренний endpoint для команд бота без проверки initData"""
    try:
        return get_matches_data()
    except Exception as e:
        log.exception("Ошибка в api_internal_matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- ОБРАБОТЧИКИ TELEGRAM ---
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
        log.info(f"🔄 Внутренний запрос к: {internal_url}")
        
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            try:
                error_data = resp.json()
                error_msg = error_data.get('error', 'Неизвестная ошибка')
            except:
                error_msg = f"HTTP ошибка {resp.status_code}"
            
            # Более понятные сообщения об ошибках
            if "API ключ" in error_msg or "401" in error_msg:
                await message.answer("❌ Проблема с API ключем. Проверьте настройки.")
            elif "Пустой ответ" in error_msg:
                await message.answer("❌ API не вернуло данные. Попробуйте позже.")
            elif "таймаут" in error_msg.lower() or "timeout" in error_msg.lower():
                await message.answer("❌ Таймаут при запросе к API.")
            elif "подключени" in error_msg.lower() or "connection" in error_msg.lower():
                await message.answer("❌ Ошибка подключения к API.")
            else:
                await message.answer(f"❌ Ошибка API: {error_msg}")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await message.answer("⚽ Нет матчей в ближайшие 2 часа.")
            return
            
        # Отправляем первые 5 матчей (ограничение Telegram)
        for m in data[:5]:
            tournament = m.get("tournament", {})
            league = tournament.get("name", "—")
            
            home_team = m.get("homeTeam", {})
            away_team = m.get("awayTeam", {})
            home_name = home_team.get("name", "Home")
            away_name = away_team.get("name", "Away")
            
            # Конвертируем timestamp в читаемое время
            start_timestamp = m.get("startTimestamp")
            if start_timestamp:
                start_time = datetime.fromtimestamp(start_timestamp / 1000)
                time_str = start_time.strftime("%H:%M")
            else:
                time_str = "—"
            
            text = f"🏆 <b>{league}</b>\n⚽ {home_name} vs {away_name}\n🕒 {time_str}"
            await message.answer(text, parse_mode="HTML")
            
        if len(data) > 5:
            await message.answer(f"📊 Показано 5 из {len(data)} матчей")
            
    except Exception as e:
        log.error(f"💥 Ошибка в cmd_matches: {e}")
        await message.answer("❌ Внутренняя ошибка при получении матчей")

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
        "- Разные лиги и турниры\n\n"
        "🛠 *Поддержка:*\n"
        "Для настройки Mini App обратитесь к администратору.",
        parse_mode="Markdown"
    )
    await callback.answer()

# --- ЗАПУСК БОТА И API ---
def run_bot():
    """Запуск бота"""
    asyncio.run(dp.start_polling(bot))

def run_api():
    """Запуск FastAPI"""
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    log.info("🚀 Запуск бота с исправленным API согласно документации")
    log.info(f"🔑 WEBAPP_URL: {WEBAPP_URL}")
    
    # Запускаем API в отдельном потоке
    t_api = threading.Thread(target=run_api, daemon=True)
    t_api.start()
    log.info("🌐 FastAPI запущен на порту 8080")
    
    # Запускаем бота
    run_bot()

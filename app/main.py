import os
import logging
import threading
import asyncio
from datetime import datetime, timedelta
import hmac
import hashlib
import json
from typing import Dict, List, Optional

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

# --- ХРАНИЛИЩА ДАННЫХ ---
user_favorites: Dict[int, List[str]] = {}
user_notifications: Dict[int, bool] = {}
user_settings: Dict[int, Dict] = {}

# --- ПРЕДОПРЕДЕЛЕННЫЕ ЛИГИ ---
POPULAR_LEAGUES = {
    "premier_league": {"id": 1, "name": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Премьер-лига Англия", "country": "Англия"},
    "la_liga": {"id": 2, "name": "🇪🇸 Ла Лига Испания", "country": "Испания"},
    "serie_a": {"id": 3, "name": "🇮🇹 Серия А Италия", "country": "Италия"},
    "bundesliga": {"id": 4, "name": "🇩🇪 Бундеслига Германия", "country": "Германия"},
    "ligue_1": {"id": 5, "name": "🇫🇷 Лига 1 Франция", "country": "Франция"},
    "rpl": {"id": 6, "name": "🇷🇺 Российская Премьер-лига", "country": "Россия"},
    "champions_league": {"id": 7, "name": "🏆 Лига Чемпионов", "country": "Европа"},
    "europa_league": {"id": 8, "name": "🥈 Лига Европы", "country": "Европa"}
}

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

# --- РАСШИРЕННАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ О МАТЧАХ ---
def get_matches_data_extended(date=None, status=None, tournament_id=None, team_id=None):
    """Расширенная функция для получения данных о матчах с фильтрами"""
    try:
        # Если дата не указана, используем сегодня
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        params = {"date": date}
        
        # Добавляем дополнительные параметры если указаны
        if status:
            params["status"] = status
        if tournament_id:
            params["tournament_id"] = tournament_id
        if team_id:
            params["team_id"] = team_id
        
        headers = {"Authorization": API_SPORT_KEY}
        url = "https://api.api-sport.ru/v1/football/matches"
        
        log.info(f"🔍 Расширенный запрос к API: {url}, параметры: {params}")
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        if resp.status_code != 200:
            log.error(f"❌ Ошибка API: {resp.status_code}")
            return JSONResponse(
                status_code=resp.status_code,
                content={"error": f"Ошибка API: {resp.status_code}"}
            )
        
        data = resp.json()
        matches = data.get("matches", [])
        
        # Для live-матчей не фильтруем по времени
        if status == 'inprogress':
            filtered_matches = matches
        else:
            # Фильтрация по московскому времени
            now_utc = datetime.utcnow()
            now_msk = now_utc + timedelta(hours=3)
            two_hours_later_msk = now_msk + timedelta(hours=2)
            
            filtered_matches = []
            for match in matches:
                start_timestamp = match.get("startTimestamp")
                if start_timestamp:
                    start_time_utc = datetime.fromtimestamp(start_timestamp / 1000)
                    start_time_msk = start_time_utc + timedelta(hours=3)
                    
                    if now_msk <= start_time_msk <= two_hours_later_msk:
                        filtered_matches.append(match)
        
        return JSONResponse(content={
            "data": filtered_matches,
            "total": len(filtered_matches),
            "today_total": len(matches)
        })
        
    except Exception as e:
        log.exception("💥 Ошибка в get_matches_data_extended")
        return JSONResponse(
            status_code=500,
            content={"error": f"Внутренняя ошибка: {str(e)}"}
        )

def get_matches_data():
    """Функция для обратной совместимости"""
    return get_matches_data_extended()

# --- API ENDPOINTS ---
@app.get("/api/matches")
def api_matches(request: Request):
    """Endpoint для Mini App с проверкой initData"""
    try:
        init_data = request.headers.get("X-Telegram-Init-Data")
        
        if not init_data or not validate_init_data(init_data):
            return JSONResponse(status_code=401, content={"error": "Неверный initData"})
        
        return get_matches_data_extended()
        
    except Exception as e:
        log.exception("Ошибка в api_matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches")
def api_internal_matches():
    """Внутренний endpoint для команд бота без проверки initData"""
    try:
        return get_matches_data_extended()
    except Exception as e:
        log.exception("Ошибка в api_internal_matches")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches/live")
def api_internal_matches_live():
    """Live-матчи"""
    try:
        return get_matches_data_extended(status='inprogress')
    except Exception as e:
        log.exception("Ошибка в api_internal_matches_live")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches/league/{league_id}")
def api_internal_matches_league(league_id: int):
    """Матчи по лиге"""
    try:
        return get_matches_data_extended(tournament_id=league_id)
    except Exception as e:
        log.exception("Ошибка в api_internal_matches_league")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- ОСНОВНЫЕ ОБРАБОТЧИКИ TELEGRAM ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    kb.button(text="📅 Ближайшие матчи", callback_data="get_matches")
    kb.button(text="📡 Live-матчи", callback_data="get_live")
    kb.button(text="🏆 Выбор лиги", callback_data="select_league")
    kb.button(text="⭐ Избранное", callback_data="favorites_menu")
    kb.button(text="📊 Статистика", callback_data="stats_menu")
    kb.button(text="⚙️ Настройки", callback_data="settings_menu")
    kb.adjust(2, 2, 2)
    
    await message.answer(
        "🤖 *Футбольный бот лудик - все функции*\n\n"
        "⚽ *Основные команды:*\n"
        "/matches - Ближайшие матчи\n"
        "/live - Текущие матчи\n"
        "/league - Выбор лиги\n"
        "/team - Поиск по команде\n\n"
        "⭐ *Дополнительные:*\n"
        "/favorite - Избранное\n"
        "/notify - Уведомления\n"
        "/table - Турнирные таблицы\n"
        "/stats - Статистика\n\n"
        "Или используйте кнопки ниже:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("matches"))
async def cmd_matches(message: types.Message):
    await message.answer("⏳ Загружаю ближайшие матчи...")
    try:
        internal_url = "http://127.0.0.1:8080/api/internal/matches"
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            await message.answer("❌ Ошибка при загрузке матчей")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await message.answer("⚽ Нет матчей в ближайшие 2 часа.")
            return
            
        for m in data[:5]:
            await send_match_message(message, m)
            
        if len(data) > 5:
            await message.answer(f"📊 Показано 5 из {len(data)} матчей")
            
    except Exception as e:
        log.error(f"Ошибка в cmd_matches: {e}")
        await message.answer("❌ Внутренняя ошибка")

@dp.message(Command("live"))
async def cmd_live(message: types.Message):
    await message.answer("📡 Загружаю текущие матчи...")
    try:
        internal_url = "http://127.0.0.1:8080/api/internal/matches/live"
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            await message.answer("❌ Ошибка при загрузке live-матчей")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await message.answer("🔴 Сейчас нет активных матчей.")
            return
            
        for m in data[:5]:
            await send_live_match_message(message, m)
            
        if len(data) > 5:
            await message.answer(f"📊 Показано 5 из {len(data)} матчей")
            
    except Exception as e:
        log.error(f"Ошибка в cmd_live: {e}")
        await message.answer("❌ Внутренняя ошибка")

@dp.message(Command("league"))
async def cmd_league(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    for league_id, league_info in POPULAR_LEAGUES.items():
        kb.button(text=league_info["name"], callback_data=f"league_{league_id}")
    
    kb.button(text="🔙 Назад", callback_data="main_menu")
    kb.adjust(2)
    
    await message.answer(
        "🏆 *Выберите лигу:*\n\n"
        "Показаны матчи на сегодня из выбранной лиги:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("team"))
async def cmd_team(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "🔍 *Поиск матчей по команде*\n\n"
            "Введите название команды:\n"
            "<code>/team Реал Мадрид</code>\n"
            "<code>/team Барселона</code>\n\n"
            "⚠️ *Внимание:* Функция в разработке",
            parse_mode="HTML"
        )
        return
    
    team_name = args[1]
    await message.answer(f"🔍 Ищу матчи для команды: <b>{team_name}</b>\n\n⚠️ Функция в разработке", parse_mode="HTML")

@dp.message(Command("favorite"))
async def cmd_favorite(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        # Показать избранное
        favorites = user_favorites.get(user_id, [])
        if favorites:
            fav_text = "\n".join([f"⭐ {team}" for team in favorites])
            await message.answer(f"⭐ *Ваши избранные команды:*\n\n{fav_text}", parse_mode="Markdown")
        else:
            await message.answer(
                "⭐ *Избранные команды*\n\n"
                "У вас нет избранных команд.\n"
                "Добавьте команду:\n"
                "<code>/favorite Реал Мадрид</code>",
                parse_mode="HTML"
            )
        return
    
    team_name = args[1]
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    
    if team_name not in user_favorites[user_id]:
        user_favorites[user_id].append(team_name)
        await message.answer(f"✅ Команда <b>{team_name}</b> добавлена в избранное", parse_mode="HTML")
    else:
        await message.answer(f"ℹ️ Команда <b>{team_name}</b> уже в избранном", parse_mode="HTML")

@dp.message(Command("notify"))
async def cmd_notify(message: types.Message):
    user_id = message.from_user.id
    current_status = user_notifications.get(user_id, False)
    
    kb = InlineKeyboardBuilder()
    
    if current_status:
        kb.button(text="🔕 Выключить уведомления", callback_data="disable_notifications")
        status_text = "включены"
    else:
        kb.button(text="🔔 Включить уведомления", callback_data="enable_notifications")
        status_text = "выключены"
    
    kb.button(text="🔙 Назад", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(
        f"🔔 *Уведомления*\n\n"
        f"Текущий статус: {status_text}\n\n"
        f"Получать уведомления о:\n"
        f"• Начале матчей избранных команд\n"
        f"• Важных событиях",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("table"))
async def cmd_table(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    for league_id, league_info in POPULAR_LEAGUES.items():
        kb.button(text=f"📊 {league_info['name']}", callback_data=f"table_{league_id}")
    
    kb.button(text="🔙 Назад", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(
        "📊 *Турнирные таблицы*\n\n"
        "Выберите лигу для просмотра таблицы:\n\n"
        "⚠️ *Внимание:* Функция в разработке",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    kb.button(text="🥅 Лучшие бомбардиры", callback_data="stats_scorers")
    kb.button(text="🅰️ Лучшие ассистенты", callback_data="stats_assists")
    kb.button(text="🟨🟥 Дисциплина", callback_data="stats_discipline")
    kb.button(text="🔙 Назад", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(
        "📈 *Статистика*\n\n"
        "Выберите тип статистики:\n\n"
        "⚠️ *Внимание:* Функция в разработке",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def send_match_message(message, match_data):
    """Отправка сообщения о матче"""
    tournament = match_data.get("tournament", {})
    league = tournament.get("name", "—")
    
    home_team = match_data.get("homeTeam", {})
    away_team = match_data.get("awayTeam", {})
    home_name = home_team.get("name", "Home")
    away_name = away_team.get("name", "Away")
    
    start_timestamp = match_data.get("startTimestamp")
    if start_timestamp:
        start_time_utc = datetime.fromtimestamp(start_timestamp / 1000)
        start_time_msk = start_time_utc + timedelta(hours=3)
        time_str = start_time_msk.strftime("%H:%M МСК")
    else:
        time_str = "—"
    
    text = f"🏆 <b>{league}</b>\n⚽ {home_name} vs {away_name}\n🕒 {time_str}"
    await message.answer(text, parse_mode="HTML")

async def send_live_match_message(message, match_data):
    """Отправка сообщения о live-матче"""
    tournament = match_data.get("tournament", {})
    league = tournament.get("name", "—")
    
    home_team = match_data.get("homeTeam", {})
    away_team = match_data.get("awayTeam", {})
    home_name = home_team.get("name", "Home")
    away_name = away_team.get("name", "Away")
    
    home_score = match_data.get("homeScore", {}).get("current", 0)
    away_score = match_data.get("awayScore", {}).get("current", 0)
    
    text = f"🔴 <b>LIVE: {league}</b>\n⚽ {home_name} {home_score} - {away_score} {away_name}\n🕒 Матч в процессе"
    await message.answer(text, parse_mode="HTML")

# --- CALLBACK ОБРАБОТЧИКИ ---
@dp.callback_query(lambda c: c.data == "get_matches")
async def process_get_matches(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_matches(callback.message)

@dp.callback_query(lambda c: c.data == "get_live")
async def process_get_live(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_live(callback.message)

@dp.callback_query(lambda c: c.data.startswith("league_"))
async def process_league_select(callback: types.CallbackQuery):
    league_key = callback.data.replace("league_", "")
    league_info = POPULAR_LEAGUES.get(league_key)
    
    if not league_info:
        await callback.answer("Лига не найдена")
        return
    
    await callback.answer(f"Загружаю матчи {league_info['name']}...")
    
    try:
        internal_url = f"http://127.0.0.1:8080/api/internal/matches/league/{league_info['id']}"
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            await callback.message.answer("❌ Ошибка при загрузке матчей лиги")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await callback.message.answer(f"⚽ Нет матчей в лиге {league_info['name']} на сегодня.")
            return
            
        await callback.message.answer(f"🏆 *Матчи {league_info['name']}:*", parse_mode="Markdown")
        
        for m in data[:5]:
            await send_match_message(callback.message, m)
            
    except Exception as e:
        log.error(f"Ошибка в process_league_select: {e}")
        await callback.message.answer("❌ Ошибка при загрузке матчей лиги")

@dp.callback_query(lambda c: c.data == "favorites_menu")
async def process_favorites_menu(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_favorite(callback.message)

@dp.callback_query(lambda c: c.data == "stats_menu")
async def process_stats_menu(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_stats(callback.message)

@dp.callback_query(lambda c: c.data == "settings_menu")
async def process_settings_menu(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_notify(callback.message)

@dp.callback_query(lambda c: c.data == "select_league")
async def process_select_league(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_league(callback.message)

@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_start(callback.message)

@dp.callback_query(lambda c: c.data == "enable_notifications")
async def process_enable_notifications(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_notifications[user_id] = True
    await callback.answer("✅ Уведомления включены")
    await cmd_notify(callback.message)

@dp.callback_query(lambda c: c.data == "disable_notifications")
async def process_disable_notifications(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_notifications[user_id] = False
    await callback.answer("🔕 Уведомления выключены")
    await cmd_notify(callback.message)

# --- ЗАПУСК БОТА И API ---
def run_bot():
    """Запуск бота"""
    asyncio.run(dp.start_polling(bot))

def run_api():
    """Запуск FastAPI"""
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    log.info("🚀 Запуск бота с расширенными функциями")
    
    # Запускаем API в отдельном потоке
    t_api = threading.Thread(target=run_api, daemon=True)
    t_api.start()
    log.info("🌐 FastAPI запущен на порту 8080")
    
    # Запускаем бота
    run_bot()

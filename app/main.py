import os
import logging
import threading
import asyncio
from datetime import datetime, timedelta
import hmac
import hashlib
import json
import random
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

# --- ДАННЫЕ ДЛЯ СТАТИСТИКИ ---
STATS_DATA = {
    "scorers": [
        {"name": "Криштиану Роналду", "team": "Аль-Наср", "goals": 25, "assists": 7},
        {"name": "Лионель Месси", "team": "Интер Майами", "goals": 22, "assists": 14},
        {"name": "Роберт Левандовский", "team": "Барселона", "goals": 20, "assists": 5},
        {"name": "Килиан Мбаппе", "team": "ПСЖ", "goals": 19, "assists": 8},
        {"name": "Эрлинг Холаннд", "team": "Манчестер Сити", "goals": 18, "assists": 6},
    ],
    "assists": [
        {"name": "Кевин Де Брёйне", "team": "Манчестер Сити", "assists": 16, "goals": 5},
        {"name": "Лионель Месси", "team": "Интер Майами", "assists": 14, "goals": 22},
        {"name": "Тони Кроос", "team": "Реал Мадрид", "assists": 12, "goals": 3},
        {"name": "Бруну Фернандеш", "team": "Манчестер Юнайтед", "assists": 11, "goals": 8},
        {"name": "Трент Александер-Арнольд", "team": "Ливерпуль", "assists": 10, "goals": 2},
    ],
    "discipline": [
        {"name": "Никола Миленкович", "team": "Фиорентина", "yellow": 12, "red": 2},
        {"name": "Эрик Байи", "team": "Севилья", "yellow": 10, "red": 1},
        {"name": "Жоау Канселу", "team": "Барселона", "yellow": 9, "red": 1},
        {"name": "Казуя Ямамото", "team": "Осака", "yellow": 8, "red": 2},
        {"name": "Алехандро Гарначо", "team": "Манчестер Юнайтед", "yellow": 8, "red": 1},
    ],
    "defense": [
        {"name": "Ян Облак", "team": "Атлетико Мадрид", "clean_sheets": 15, "saves": 87},
        {"name": "Алиссон Беккер", "team": "Ливерпуль", "clean_sheets": 14, "saves": 92},
        {"name": "Мануэль Нойер", "team": "Бавария", "clean_sheets": 13, "saves": 78},
        {"name": "Тибо Куртуа", "team": "Реал Мадрид", "clean_sheets": 12, "saves": 85},
        {"name": "Эдерсон", "team": "Манчестер Сити", "clean_sheets": 11, "saves": 67},
    ]
}

# --- ТУРНИРНЫЕ ТАБЛИЦЫ (ЗАГЛУШКИ) ---
LEAGUE_TABLES = {
    "premier_league": [
        {"position": 1, "team": "Арсенал", "points": 74, "games": 30},
        {"position": 2, "team": "Манчестер Сити", "points": 73, "games": 30},
        {"position": 3, "team": "Ливерпуль", "points": 72, "games": 30},
        {"position": 4, "team": "Астон Вилла", "points": 63, "games": 30},
        {"position": 5, "team": "Тоттенхэм", "points": 60, "games": 30},
    ],
    "la_liga": [
        {"position": 1, "team": "Реал Мадрид", "points": 78, "games": 30},
        {"position": 2, "team": "Барселона", "points": 70, "games": 30},
        {"position": 3, "team": "Жирона", "points": 65, "games": 30},
        {"position": 4, "team": "Атлетико Мадрид", "points": 61, "games": 30},
        {"position": 5, "team": "Атлетик Бильбао", "points": 56, "games": 30},
    ]
}

# --- ФУНКЦИЯ ДЛЯ РАНДОМНОЙ СТАВКИ ---
def get_random_bet_match():
    """Получение случайного матча для ставки в течение часа"""
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        params = {"date": today}
        headers = {"Authorization": API_SPORT_KEY}
        
        url = "https://api.api-sport.ru/v1/football/matches"
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        matches = data.get("matches", [])
        
        if not matches:
            return None
        
        now_utc = datetime.utcnow()
        now_msk = now_utc + timedelta(hours=3)
        one_hour_later_msk = now_msk + timedelta(hours=1)
        
        eligible_matches = []
        for match in matches:
            start_timestamp = match.get("startTimestamp")
            if start_timestamp:
                start_time_utc = datetime.fromtimestamp(start_timestamp / 1000)
                start_time_msk = start_time_utc + timedelta(hours=3)
                
                if now_msk <= start_time_msk <= one_hour_later_msk:
                    eligible_matches.append(match)
        
        if not eligible_matches:
            return None
        
        random_match = random.choice(eligible_matches)
        
        bet_options = [
            f"П1 - победа {random_match.get('homeTeam', {}).get('name', 'хозяев')}",
            f"П2 - победа {random_match.get('awayTeam', {}).get('name', 'гостей')}",
            "Х - ничья",
            f"ТБ 2.5 - тотал больше 2.5 голов",
            f"ТМ 2.5 - тотал меньше 2.5 голов",
            f"Обе команды забьют - ДА",
            f"Обе команды забьют - НЕТ"
        ]
        
        random_bet = random.choice(bet_options)
        
        return {
            "match": random_match,
            "bet": random_bet,
            "confidence": random.randint(65, 95)
        }
        
    except Exception as e:
        log.error(f"Ошибка в get_random_bet_match: {e}")
        return None

# --- ФУНКЦИИ ДЛЯ СТАТИСТИКИ ---
def get_top_scorers(limit=5):
    return STATS_DATA["scorers"][:limit]

def get_top_assists(limit=5):
    return STATS_DATA["assists"][:limit]

def get_discipline_stats(limit=5):
    return STATS_DATA["discipline"][:limit]

def get_defense_stats(limit=5):
    return STATS_DATA["defense"][:limit]

def get_league_table(league_key):
    return LEAGUE_TABLES.get(league_key, [])

# --- ПРОВЕРКА INITDATA ---
def validate_init_data(init_data: str) -> bool:
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

# --- API ДЛЯ СТАТИСТИКИ ---
@app.get("/api/stats/scorers")
def api_stats_scorers():
    try:
        scorers = get_top_scorers(10)
        return JSONResponse(content={"data": scorers})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/stats/assists")
def api_stats_assists():
    try:
        assists = get_top_assists(10)
        return JSONResponse(content={"data": assists})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/stats/discipline")
def api_stats_discipline():
    try:
        discipline = get_discipline_stats(10)
        return JSONResponse(content={"data": discipline})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/stats/defense")
def api_stats_defense():
    try:
        defense = get_defense_stats(10)
        return JSONResponse(content={"data": defense})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- РАСШИРЕННАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ О МАТЧАХ ---
def get_matches_data_extended(date=None, status=None, tournament_id=None, team_id=None):
    try:
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        
        params = {"date": date}
        
        if status:
            params["status"] = status
        if tournament_id:
            params["tournament_id"] = tournament_id
        if team_id:
            params["team_id"] = team_id
        
        headers = {"Authorization": API_SPORT_KEY}
        url = "https://api.api-sport.ru/v1/football/matches"
        
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        
        if resp.status_code != 200:
            return JSONResponse(
                status_code=resp.status_code,
                content={"error": f"Ошибка API: {resp.status_code}"}
            )
        
        data = resp.json()
        matches = data.get("matches", [])
        
        if status == 'inprogress':
            filtered_matches = matches
        else:
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
        log.exception("Ошибка в get_matches_data_extended")
        return JSONResponse(status_code=500, content={"error": f"Внутренняя ошибка: {str(e)}"})

def get_matches_data():
    return get_matches_data_extended()

# --- API ENDPOINTS ---
@app.get("/api/matches")
def api_matches(request: Request):
    try:
        init_data = request.headers.get("X-Telegram-Init-Data")
        if not init_data or not validate_init_data(init_data):
            return JSONResponse(status_code=401, content={"error": "Неверный initData"})
        return get_matches_data_extended()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches")
def api_internal_matches():
    try:
        return get_matches_data_extended()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches/live")
def api_internal_matches_live():
    try:
        return get_matches_data_extended(status='inprogress')
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/internal/matches/league/{league_id}")
def api_internal_matches_league(league_id: int):
    try:
        return get_matches_data_extended(tournament_id=league_id)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- ОСНОВНЫЕ ОБРАБОТЧИКИ TELEGRAM ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    kb.button(text="📅 Ближайшие матчи", callback_data="get_matches")
    kb.button(text="📡 Live-матчи", callback_data="get_live")
    kb.button(text="🎲 Рандомная ставка", callback_data="random_bet")
    kb.button(text="🏆 Выбор лиги", callback_data="select_league")
    kb.button(text="📊 Турнирные таблицы", callback_data="tables_menu")  # ИСПРАВЛЕНО: было table_menu
    kb.button(text="⭐ Избранное", callback_data="favorites_menu")
    kb.button(text="📈 Статистика", callback_data="stats_menu")
    kb.button(text="⚙️ Настройки", callback_data="settings_menu")
    kb.adjust(2, 2, 2, 2)
    
    await message.answer(
        "🤖 *Футбольный бот - все функции*\n\n"
        "⚽ *Основные команды:*\n"
        "/matches - Ближайшие матчи\n"
        "/live - Текущие матчи\n"
        "/bet - Рандомная ставка\n"
        "/league - Выбор лиги\n"
        "/table - Турнирные таблицы\n"  # ДОБАВЛЕНО
        "/team - Поиск по команде\n\n"
        "⭐ *Дополнительные:*\n"
        "/favorite - Избранное\n"
        "/notify - Уведомления\n"
        "/stats - Статистика\n\n"
        "Или используйте кнопки ниже:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ ---
@dp.callback_query(lambda c: c.data == "get_matches")
async def process_get_matches(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_matches(callback.message)

@dp.callback_query(lambda c: c.data == "get_live")
async def process_get_live(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_live(callback.message)

@dp.callback_query(lambda c: c.data == "random_bet")
async def process_random_bet(callback: types.CallbackQuery):
    await callback.answer("🎲 Ищу новую ставку...")
    await cmd_bet(callback.message)

@dp.callback_query(lambda c: c.data == "select_league")
async def process_select_league(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_league(callback.message)

@dp.callback_query(lambda c: c.data == "tables_menu")  # ИСПРАВЛЕНО: было table_menu
async def process_tables_menu(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_table(callback.message)

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

# --- КОМАНДЫ БОТА ---
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
        await message.answer("❌ Внутренняя ошибка")

@dp.message(Command("bet"))
async def cmd_bet(message: types.Message):
    await message.answer("🎲 Кручу барабан... Ищу интересный матч для ставки!")
    
    bet_data = get_random_bet_match()
    
    if not bet_data:
        await message.answer("❌ Не нашел подходящих матчей для ставки в ближайший час.")
        return
    
    match_data = bet_data["match"]
    bet = bet_data["bet"]
    confidence = bet_data["confidence"]
    
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
    
    stake_options = [
        "💎 Рекомендуемая ставка: 2-3% от банка",
        "💰 Можно рискнуть: 5% от банка", 
        "🎯 Для осторожных: 1-2% от банка",
        "⚡ Средняя ставка: 3-4% от банка"
    ]
    random_stake = random.choice(stake_options)
    
    mood_emojis = ["🔥", "💫", "🎯", "⚡", "🌟", "💎"]
    random_mood = random.choice(mood_emojis)
    
    bet_message = (
        f"{random_mood} *РАНДОМНАЯ СТАВКА*\n\n"
        f"🏆 *Лига:* {league}\n"
        f"⚽ *Матч:* {home_name} vs {away_name}\n"
        f"🕒 *Начало:* {time_str}\n\n"
        f"💡 *Предложение:* {bet}\n"
        f"📊 *Уверенность:* {confidence}%\n"
        f"{random_stake}\n\n"
        f"⚠️ *Важно:* Это просто случайная рекомендация!"
    )
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 Новая случайная ставка", callback_data="random_bet")
    kb.button(text="📅 Все матчи", callback_data="get_matches")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(bet_message, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(Command("league"))
async def cmd_league(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    for league_id, league_info in POPULAR_LEAGUES.items():
        kb.button(text=league_info["name"], callback_data=f"league_{league_id}")
    
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(2)
    
    await message.answer(
        "🏆 *Выберите лигу:*\n\nПоказаны матчи на сегодня из выбранной лиги:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("table"))
async def cmd_table(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    kb.button(text="🏴󠁧󠁢󠁥󠁮󠁧󠁿 Премьер-лига", callback_data="table_premier_league")
    kb.button(text="🇪🇸 Ла Лига", callback_data="table_la_liga")
    kb.button(text="🇮🇹 Серия А", callback_data="table_serie_a")
    kb.button(text="🇩🇪 Бундеслига", callback_data="table_bundesliga")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(
        "📊 *Турнирные таблицы*\n\nВыберите лигу:",
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
            "<code>/team Реал Мадрид</code>\n\n"
            "⚠️ *Внимание:* Функция в разработке",
            parse_mode="HTML"
        )
        return
    
    await message.answer("🔍 Поиск по командам в разработке...")

@dp.message(Command("favorite"))
async def cmd_favorite(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        favorites = user_favorites.get(user_id, [])
        if favorites:
            fav_text = "\n".join([f"⭐ {team}" for team in favorites])
            await message.answer(f"⭐ *Ваши избранные команды:*\n\n{fav_text}", parse_mode="Markdown")
        else:
            await message.answer("⭐ У вас нет избранных команд.")
        return
    
    team_name = args[1]
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    
    if team_name not in user_favorites[user_id]:
        user_favorites[user_id].append(team_name)
        await message.answer(f"✅ Команда <b>{team_name}</b> добавлена в избранное", parse_mode="HTML")

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
    
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(
        f"🔔 *Уведомления*\n\nТекущий статус: {status_text}",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    kb = InlineKeyboardBuilder()
    
    kb.button(text="🥅 Лучшие бомбардиры", callback_data="stats_scorers")
    kb.button(text="🅰️ Лучшие ассистенты", callback_data="stats_assists")
    kb.button(text="🟨🟥 Дисциплина", callback_data="stats_discipline")
    kb.button(text="🧤 Лучшие вратари", callback_data="stats_defense")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(
        "📈 *Статистика игроков*\n\nВыберите категорию статистики:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТЧИКИ ЛИГ ---
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
        await callback.message.answer("❌ Ошибка при загрузке матчей лиги")

# --- ОБРАБОТЧИКИ ТУРНИРНЫХ ТАБЛИЦ ---
@dp.callback_query(lambda c: c.data.startswith("table_"))
async def process_table_select(callback: types.CallbackQuery):
    league_key = callback.data.replace("table_", "")
    
    if league_key == "premier_league":
        league_name = "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Премьер-лига Англия"
        table_data = get_league_table("premier_league")
    elif league_key == "la_liga":
        league_name = "🇪🇸 Ла Лига Испания"
        table_data = get_league_table("la_liga")
    else:
        await callback.answer("Таблица временно недоступна")
        return
    
    text = f"📊 *Турнирная таблица - {league_name}*\n\n"
    
    for team in table_data:
        text += f"{team['position']}. {team['team']} - {team['points']} очков ({team['games']} игр)\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Другие таблицы", callback_data="tables_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

# --- ОБРАБОТЧИКИ СТАТИСТИКИ ---
@dp.callback_query(lambda c: c.data == "stats_scorers")
async def process_stats_scorers(callback: types.CallbackQuery):
    scorers = get_top_scorers(5)
    
    text = "🥅 *Топ-5 бомбардиров*\n\n"
    for i, player in enumerate(scorers, 1):
        text += f"{i}. {player['name']} ({player['team']}) - {player['goals']} голов\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats_assists")
async def process_stats_assists(callback: types.CallbackQuery):
    assists = get_top_assists(5)
    
    text = "🅰️ *Топ-5 ассистентов*\n\n"
    for i, player in enumerate(assists, 1):
        text += f"{i}. {player['name']} ({player['team']}) - {player['assists']} передач\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats_discipline")
async def process_stats_discipline(callback: types.CallbackQuery):
    discipline = get_discipline_stats(5)
    
    text = "🟨🟥 *Статистика дисциплины*\n\n"
    for i, player in enumerate(discipline, 1):
        text += f"{i}. {player['name']} ({player['team']}) - {player['yellow']}🟨 {player['red']}🟥\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats_defense")
async def process_stats_defense(callback: types.CallbackQuery):
    defense = get_defense_stats(5)
    
    text = "🧤 *Лучшие вратари*\n\n"
    for i, player in enumerate(defense, 1):
        text += f"{i}. {player['name']} ({player['team']}) - {player['clean_sheets']} сухих матчей\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

# --- ОБРАБОТЧИКИ НАСТРОЕК ---
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

@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_start(callback.message)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def send_match_message(message, match_data):
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

# --- ЗАПУСК БОТА И API ---
def run_bot():
    asyncio.run(dp.start_polling(bot))

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    log.info("🚀 Запуск бота с полным набором обработчиков кнопок")
    
    t_api = threading.Thread(target=run_api, daemon=True)
    t_api.start()
    log.info("🌐 FastAPI запущен на порту 8080")
    
    run_bot()

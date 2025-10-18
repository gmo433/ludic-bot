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
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats
from aiogram.enums import ChatType

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

# --- НАСТРОЙКА МЕНЮ БОТА ---
async def set_bot_commands():
    """Установка команд меню бота"""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="matches", description="📅 Ближайшие матчи"),
        BotCommand(command="live", description="📡 Live-матчи"),
        BotCommand(command="bet", description="🎲 Случайная ставка"),
        BotCommand(command="league", description="🏆 Выбор лиги"),
        BotCommand(command="stats", description="📈 Статистика игроков"),
        BotCommand(command="table", description="📊 Турнирные таблицы"),
        BotCommand(command="favorite", description="⭐ Избранное"),
        BotCommand(command="notify", description="🔔 Уведомления"),
        BotCommand(command="menu", description="📱 Главное меню")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

async def set_group_commands():
    """Установка команд для групп"""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="matches", description="📅 Ближайшие матчи"),
        BotCommand(command="bet", description="🎲 Случайная ставка"),
        BotCommand(command="menu", description="📱 Показать меню")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())

app = FastAPI()

# --- ХРАНИЛИЩА ДАННЫХ ---
user_favorites: Dict[int, List[str]] = {}
user_notifications: Dict[int, bool] = {}
user_settings: Dict[int, Dict] = {}

# --- ПРЕДОПРЕДЕЛЕННЫЕ ЛИГИ ---
POPULAR_LEAGUES = {
    "premier_league": {"id": 1, "name": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Премьер-лига", "country": "Англия", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "la_liga": {"id": 2, "name": "🇪🇸 Ла Лига", "country": "Испания", "emoji": "🇪🇸"},
    "serie_a": {"id": 3, "name": "🇮🇹 Серия А", "country": "Италия", "emoji": "🇮🇹"},
    "bundesliga": {"id": 4, "name": "🇩🇪 Бундеслига", "country": "Германия", "emoji": "🇩🇪"},
    "ligue_1": {"id": 5, "name": "🇫🇷 Лига 1", "country": "Франция", "emoji": "🇫🇷"},
    "rpl": {"id": 6, "name": "🇷🇺 РПЛ", "country": "Россия", "emoji": "🇷🇺"},
    "champions_league": {"id": 7, "name": "🏆 Лига Чемпионов", "country": "Европа", "emoji": "🏆"},
    "europa_league": {"id": 8, "name": "🥈 Лига Европы", "country": "Европa", "emoji": "🥈"}
}

# --- ДАННЫЕ ДЛЯ СТАТИСТИКИ ---
STATS_DATA = {
    "scorers": [
        {"name": "Криштиану Роналду", "team": "Аль-Наср", "goals": 25, "assists": 7, "emoji": "👑"},
        {"name": "Лионель Месси", "team": "Интер Майами", "goals": 22, "assists": 14, "emoji": "⭐"},
        {"name": "Роберт Левандовский", "team": "Барселона", "goals": 20, "assists": 5, "emoji": "🔥"},
        {"name": "Килиан Мбаппе", "team": "ПСЖ", "goals": 19, "assists": 8, "emoji": "⚡"},
        {"name": "Эрлинг Холаннд", "team": "Манчестер Сити", "goals": 18, "assists": 6, "emoji": "💥"},
    ],
    "assists": [
        {"name": "Кевин Де Брёйне", "team": "Манчестер Сити", "assists": 16, "goals": 5, "emoji": "🎯"},
        {"name": "Лионель Месси", "team": "Интер Майами", "assists": 14, "goals": 22, "emoji": "⭐"},
        {"name": "Тони Кроос", "team": "Реал Мадрид", "assists": 12, "goals": 3, "emoji": "🎩"},
        {"name": "Бруну Фернандеш", "team": "Манчестер Юнайтед", "assists": 11, "goals": 8, "emoji": "🔮"},
        {"name": "Трент Александер-Арнольд", "team": "Ливерпуль", "assists": 10, "goals": 2, "emoji": "🎯"},
    ],
    "discipline": [
        {"name": "Никола Миленкович", "team": "Фиорентина", "yellow": 12, "red": 2, "emoji": "💥"},
        {"name": "Эрик Байи", "team": "Севилья", "yellow": 10, "red": 1, "emoji": "⚡"},
        {"name": "Жоау Канселу", "team": "Барселона", "yellow": 9, "red": 1, "emoji": "🔴"},
        {"name": "Казуя Ямамото", "team": "Осака", "yellow": 8, "red": 2, "emoji": "💢"},
        {"name": "Алехандро Гарначо", "team": "Манчестер Юнайтед", "yellow": 8, "red": 1, "emoji": "⚡"},
    ],
    "defense": [
        {"name": "Ян Облак", "team": "Атлетико Мадрид", "clean_sheets": 15, "saves": 87, "emoji": "🛡️"},
        {"name": "Алиссон Беккер", "team": "Ливерпуль", "clean_sheets": 14, "saves": 92, "emoji": "🌟"},
        {"name": "Мануэль Нойер", "team": "Бавария", "clean_sheets": 13, "saves": 78, "emoji": "🧤"},
        {"name": "Тибо Куртуа", "team": "Реал Мадрид", "clean_sheets": 12, "saves": 85, "emoji": "⭐"},
        {"name": "Эдерсон", "team": "Манчестер Сити", "clean_sheets": 11, "saves": 67, "emoji": "⚡"},
    ]
}

# --- ТУРНИРНЫЕ ТАБЛИЦЫ ---
LEAGUE_TABLES = {
    "premier_league": [
        {"position": 1, "team": "Арсенал", "points": 74, "games": 30, "form": "WWLWW"},
        {"position": 2, "team": "Манчестер Сити", "points": 73, "games": 30, "form": "WWWDW"},
        {"position": 3, "team": "Ливерпуль", "points": 72, "games": 30, "form": "WWLWD"},
        {"position": 4, "team": "Астон Вилла", "points": 63, "games": 30, "form": "WLWWW"},
        {"position": 5, "team": "Тоттенхэм", "points": 60, "games": 30, "form": "WLLWD"},
    ],
    "la_liga": [
        {"position": 1, "team": "Реал Мадрид", "points": 78, "games": 30, "form": "WWWWW"},
        {"position": 2, "team": "Барселона", "points": 70, "games": 30, "form": "WWLWD"},
        {"position": 3, "team": "Жирона", "points": 65, "games": 30, "form": "WLLWW"},
        {"position": 4, "team": "Атлетико Мадрид", "points": 61, "games": 30, "form": "WLWWL"},
        {"position": 5, "team": "Атлетик Бильбао", "points": 56, "games": 30, "form": "WWDDW"},
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
            {"type": "П1", "text": f"П1 - победа {random_match.get('homeTeam', {}).get('name', 'хозяев')}", "emoji": "🏠"},
            {"type": "П2", "text": f"П2 - победа {random_match.get('awayTeam', {}).get('name', 'гостей')}", "emoji": "✈️"},
            {"type": "Х", "text": "Х - ничья", "emoji": "🤝"},
            {"type": "ТБ", "text": "ТБ 2.5 - тотал больше 2.5 голов", "emoji": "📈"},
            {"type": "ТМ", "text": "ТМ 2.5 - тотал меньше 2.5 голов", "emoji": "📉"},
            {"type": "ОЗ", "text": "Обе команды забьют - ДА", "emoji": "⚽⚽"},
            {"type": "ОЗ", "text": "Обе команды забьют - НЕТ", "emoji": "🚫"}
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

# --- УЛУЧШЕННЫЙ ВИЗУАЛ - ФУНКЦИИ ФОРМАТИРОВАНИЯ ---
def format_match_message(match_data, is_live=False):
    """Форматирование сообщения о матче с улучшенным визуалом"""
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
    
    if is_live:
        home_score = match_data.get("homeScore", {}).get("current", 0)
        away_score = match_data.get("awayScore", {}).get("current", 0)
        
        # Эмодзи для статуса матча
        status_emoji = "🔴"
        if home_score > away_score:
            status_emoji = "🔵"
        elif away_score > home_score:
            status_emoji = "🟡"
        else:
            status_emoji = "⚪"
        
        return (
            f"{status_emoji} *LIVE: {league}*\n"
            f"────────────────\n"
            f"🏠 *{home_name}*   {home_score} - {away_score}   *{away_name}* ✈️\n"
            f"⏰ *Время:* {time_str}\n"
            f"🎯 *Статус:* Матч в процессе"
        )
    else:
        # Эмодзи для времени до матча
        time_emoji = "🕒"
        if start_timestamp:
            time_diff = (start_time_msk - (datetime.utcnow() + timedelta(hours=3))).total_seconds() / 60
            if time_diff < 30:
                time_emoji = "🔜"
            elif time_diff < 60:
                time_emoji = "⏳"
        
        return (
            f"⚽ *{league}*\n"
            f"────────────────\n"
            f"🏠 *{home_name}*   vs   *{away_name}* ✈️\n"
            f"{time_emoji} *Начало:* {time_str}"
        )

def format_stats_message(stats_type, data):
    """Форматирование статистики с улучшенным визуалом"""
    titles = {
        "scorers": "🥅 Топ-5 бомбардиров",
        "assists": "🅰️ Топ-5 ассистентов", 
        "discipline": "🟨🟥 Статистика дисциплины",
        "defense": "🧤 Лучшие вратари"
    }
    
    text = f"*{titles.get(stats_type, 'Статистика')}*\n"
    text += "────────────────\n"
    
    for i, player in enumerate(data, 1):
        emoji = player.get('emoji', '👤')
        if stats_type == "scorers":
            text += f"{i}. {emoji} *{player['name']}* ({player['team']})\n   ⚽ Голы: {player['goals']} | 🎯 Пасы: {player['assists']}\n\n"
        elif stats_type == "assists":
            text += f"{i}. {emoji} *{player['name']}* ({player['team']})\n   🎯 Пасы: {player['assists']} | ⚽ Голы: {player['goals']}\n\n"
        elif stats_type == "discipline":
            text += f"{i}. {emoji} *{player['name']}* ({player['team']})\n   🟨 {player['yellow']} | 🟥 {player['red']}\n\n"
        elif stats_type == "defense":
            text += f"{i}. {emoji} *{player['name']}* ({player['team']})\n   🧤 Сухие матчи: {player['clean_sheets']}\n\n"
    
    text += f"📅 *Обновлено:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    return text

def format_table_message(league_name, table_data):
    """Форматирование турнирной таблицы с улучшенным визуалом"""
    position_emojis = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣"}
    
    text = f"📊 *Турнирная таблица - {league_name}*\n"
    text += "────────────────────\n"
    
    for team in table_data:
        pos = team['position']
        emoji = position_emojis.get(pos, f"{pos}️⃣")
        
        # Форматирование формы команды с эмодзи
        form_emojis = {
            'W': '🟢',  # победа
            'D': '🟡',  # ничья  
            'L': '🔴'   # поражение
        }
        form_display = ''.join([form_emojis.get(char, '⚪') for char in team.get('form', '')])
        
        text += f"{emoji} *{team['team']}*\n"
        text += f"   📊 Очки: {team['points']} | 🎮 Игры: {team['games']}\n"
        text += f"   📈 Форма: {form_display}\n\n"
    
    return text

# --- ОСНОВНЫЕ ОБРАБОТЧИКИ TELEGRAM ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Проверяем тип чата
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await cmd_start_group(message)
    else:
        await cmd_start_private(message)

async def cmd_start_private(message: types.Message):
    """Обработчик команды /start в личных сообщениях"""
    kb = InlineKeyboardBuilder()
    
    # Первый ряд - основные функции
    kb.button(text="📅 Ближайшие матчи", callback_data="get_matches")
    kb.button(text="📡 Live-матчи", callback_data="get_live")
    
    # Второй ряд - развлечения и аналитика
    kb.button(text="🎲 Рандомная ставка", callback_data="random_bet")
    kb.button(text="🏆 Выбор лиги", callback_data="select_league")
    
    # Третий ряд - статистика
    kb.button(text="📊 Турнирные таблицы", callback_data="tables_menu")
    kb.button(text="📈 Статистика игроков", callback_data="stats_menu")
    
    # Четвертый ряд - персонализация
    kb.button(text="⭐ Избранное", callback_data="favorites_menu")
    kb.button(text="⚙️ Настройки", callback_data="settings_menu")
    
    kb.adjust(2, 2, 2, 2)
    
    welcome_text = (
        "⚽ *Добро пожаловать в Футбольный Бот Лудик!* ⚽\n\n"
        "🎯 *Ваш персональный помощник в мире футбола*\n\n"
        "✨ *Доступные функции:*\n"
        "• 📅 Ближайшие матчи\n"  
        "• 📡 Прямые трансляции\n"
        "• 🎲 Случайные ставки\n"
        "• 🏆 Матчи по лигам\n"
        "• 📊 Турнирные таблицы\n"
        "• 📈 Статистика игроков\n"
        "• ⭐ Персональное избранное\n\n"
        "👇 Выберите действие ниже или используйте команды:"
    )
    
    await message.answer(welcome_text, reply_markup=kb.as_markup(), parse_mode="Markdown")

async def cmd_start_group(message: types.Message):
    """Обработчик команды /start в группах"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Запустить бота", url=f"https://t.me/{(await bot.get_me()).username}?start=start")
    
    welcome_text = (
        "⚽ *Футбольный Бот Лудик* ⚽\n\n"
        "🎯 *Ваш персональный помощник в мире футбола*\n\n"
        "✨ *Доступные функции:*\n"
        "• 📅 Ближайшие матчи\n"  
        "• 📡 Прямые трансляции\n"
        "• 🎲 Случайные ставки\n"
        "• 🏆 Матчи по лигам\n"
        "• 📊 Турнирные таблицы\n"
        "• 📈 Статистика игроков\n\n"
        "👇 Нажмите кнопку ниже чтобы начать:"
    )
    
    await message.answer(welcome_text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    """Показывает кнопку меню в группе"""
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        kb = InlineKeyboardBuilder()
        kb.button(text="⚽ Открыть футбольный бот", url=f"https://t.me/{(await bot.get_me()).username}?start=group")
        kb.button(text="📅 Ближайшие матчи", callback_data="get_matches")
        kb.button(text="🎲 Случайная ставка", callback_data="random_bet")
        kb.adjust(1, 2)
        
        await message.answer(
            "🎯 *Футбольный Бот - Быстрый доступ*\n\n"
            "Выберите действие:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await cmd_start_private(message)

# --- ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ ---
@dp.callback_query(lambda c: c.data == "get_matches")
async def process_get_matches(callback: types.CallbackQuery):
    await callback.answer("⏳ Загружаю матчи...")
    await cmd_matches(callback.message)

@dp.callback_query(lambda c: c.data == "get_live")
async def process_get_live(callback: types.CallbackQuery):
    await callback.answer("📡 Ищу live-матчи...")
    await cmd_live(callback.message)

@dp.callback_query(lambda c: c.data == "random_bet")
async def process_random_bet(callback: types.CallbackQuery):
    await callback.answer("🎲 Кручу барабан...")
    await cmd_bet(callback.message)

@dp.callback_query(lambda c: c.data == "select_league")
async def process_select_league(callback: types.CallbackQuery):
    await callback.answer("🏆 Выбираю лиги...")
    await cmd_league(callback.message)

@dp.callback_query(lambda c: c.data == "tables_menu")
async def process_tables_menu(callback: types.CallbackQuery):
    await callback.answer("📊 Загружаю таблицы...")
    await cmd_table(callback.message)

@dp.callback_query(lambda c: c.data == "stats_menu")
async def process_stats_menu(callback: types.CallbackQuery):
    await callback.answer("📈 Открываю статистику...")
    await cmd_stats(callback.message)

@dp.callback_query(lambda c: c.data == "favorites_menu")
async def process_favorites_menu(callback: types.CallbackQuery):
    await callback.answer("⭐ Ваше избранное...")
    await cmd_favorite(callback.message)

@dp.callback_query(lambda c: c.data == "settings_menu")
async def process_settings_menu(callback: types.CallbackQuery):
    await callback.answer("⚙️ Настройки...")
    await cmd_notify(callback.message)

# --- КОМАНДЫ БОТА ---
@dp.message(Command("matches"))
async def cmd_matches(message: types.Message):
    await message.answer("🔍 *Ищу ближайшие матчи...*", parse_mode="Markdown")
    
    try:
        internal_url = "http://127.0.0.1:8080/api/internal/matches"
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            await message.answer("❌ *Не удалось загрузить матчи*", parse_mode="Markdown")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await message.answer(
                "⚽ *Нет матчей в ближайшие 2 часа*\n\n"
                "Попробуйте позже или посмотрите другие разделы!",
                parse_mode="Markdown"
            )
            return
        
        await message.answer(f"📅 *Найдено матчей: {len(data)}*", parse_mode="Markdown")
        
        for m in data[:5]:
            match_text = format_match_message(m)
            await message.answer(match_text, parse_mode="Markdown")
            
        if len(data) > 5:
            kb = InlineKeyboardBuilder()
            kb.button(text="📋 Показать все матчи", callback_data="show_all_matches")
            kb.button(text="🔙 Главное меню", callback_data="main_menu")
            kb.adjust(1)
            
            await message.answer(
                f"📊 *Показано 5 из {len(data)} матчей*\n"
                f"Для просмотра всех матчей используйте кнопку ниже:",
                reply_markup=kb.as_markup(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await message.answer("❌ *Произошла ошибка при загрузке матчей*", parse_mode="Markdown")

@dp.message(Command("live"))
async def cmd_live(message: types.Message):
    await message.answer("🔴 *Ищу активные матчи...*", parse_mode="Markdown")
    
    try:
        internal_url = "http://127.0.0.1:8080/api/internal/matches/live"
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            await message.answer("❌ *Не удалось загрузить live-матчи*", parse_mode="Markdown")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await message.answer(
                "🔴 *Сейчас нет активных матчей*\n\n"
                "Но вы можете посмотреть:\n"
                "• 📅 Ближайшие матчи\n"
                "• 🎲 Случайную ставку\n"
                "• 📊 Статистику игроков",
                parse_mode="Markdown"
            )
            return
        
        await message.answer(f"🔴 *Активных матчей: {len(data)}*", parse_mode="Markdown")
        
        for m in data[:5]:
            match_text = format_match_message(m, is_live=True)
            await message.answer(match_text, parse_mode="Markdown")
            
    except Exception as e:
        await message.answer("❌ *Произошла ошибка при загрузке live-матчей*", parse_mode="Markdown")

@dp.message(Command("bet"))
async def cmd_bet(message: types.Message):
    await message.answer("🎰 *Кручу барабан... Ищу интересный матч для ставки!*", parse_mode="Markdown")
    
    bet_data = get_random_bet_match()
    
    if not bet_data:
        await message.answer(
            "❌ *Не нашел подходящих матчей для ставки в ближайший час*\n\n"
            "💡 Попробуйте позже, когда будет больше матчей!",
            parse_mode="Markdown"
        )
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
    
    # Улучшенные варианты ставок
    stake_options = [
        "💎 *Консервативно:* 1-2% от банка",
        "💰 *Сбалансированно:* 2-3% от банка", 
        "🎯 *Агрессивно:* 3-5% от банка",
        "⚡ *Максимально:* 5% от банка"
    ]
    random_stake = random.choice(stake_options)
    
    # Эмодзи для уровня уверенности
    if confidence >= 90:
        confidence_emoji = "🔮"
    elif confidence >= 80:
        confidence_emoji = "🎯"
    elif confidence >= 70:
        confidence_emoji = "📊"
    else:
        confidence_emoji = "🎲"
    
    bet_message = (
        f"🎰 *СЛУЧАЙНАЯ СТАВКА*\n"
        f"────────────────\n"
        f"🏆 *Лига:* {league}\n"
        f"⚽ *Матч:* {home_name} vs {away_name}\n"
        f"🕒 *Начало:* {time_str}\n\n"
        f"💡 *Рекомендация:* {bet['emoji']} {bet['text']}\n"
        f"{confidence_emoji} *Уверенность:* {confidence}%\n"
        f"{random_stake}\n\n"
        f"⚠️ *Важно:* Это просто случайная рекомендация!\n"
        f"🎭 Азартные игры могут вызывать зависимость!"
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
        kb.button(text=f"{league_info['emoji']} {league_info['name']}", callback_data=f"league_{league_id}")
    
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(2)
    
    await message.answer(
        "🏆 *Выберите лигу*\n\n"
        "👇 Показаны матчи на сегодня из выбранной лиги:",
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
        "📊 *Турнирные таблицы*\n\n"
        "👇 Выберите лигу для просмотра текущей таблицы:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.message(Command("team"))
async def cmd_team(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "🔍 *Поиск матчей по команде*\n\n"
            "💡 *Использование:*\n"
            "`/team Реал Мадрид`\n"
            "`/team Барселона`\n\n"
            "🚧 *Функция в разработке*\n"
            "Скоро вы сможете искать матчи по вашим любимым командам!",
            parse_mode="Markdown"
        )
        return
    
    await message.answer(
        "🔍 *Поиск по командам*\n\n"
        "🚧 *Функция в разработке*\n"
        "Следите за обновлениями!",
        parse_mode="Markdown"
    )

@dp.message(Command("favorite"))
async def cmd_favorite(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        favorites = user_favorites.get(user_id, [])
        if favorites:
            fav_text = "\n".join([f"⭐ {team}" for team in favorites])
            await message.answer(
                f"⭐ *Ваши избранные команды*\n\n"
                f"{fav_text}\n\n"
                f"💡 Чтобы добавить команду:\n"
                f"`/favorite Название команды`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "⭐ *Избранные команды*\n\n"
                "У вас пока нет избранных команд.\n\n"
                "💡 *Добавить команду:*\n"
                "`/favorite Реал Мадрид`\n"
                "`/favorite Барселона`",
                parse_mode="Markdown"
            )
        return
    
    team_name = args[1]
    if user_id not in user_favorites:
        user_favorites[user_id] = []
    
    if team_name not in user_favorites[user_id]:
        user_favorites[user_id].append(team_name)
        await message.answer(
            f"✅ *Команда добавлена в избранное*\n\n"
            f"⭐ {team_name}\n\n"
            f"Теперь вы будете получать уведомления о матчах этой команды!",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"ℹ️ *Команда уже в избранном*\n\n"
            f"⭐ {team_name}",
            parse_mode="Markdown"
        )

@dp.message(Command("notify"))
async def cmd_notify(message: types.Message):
    user_id = message.from_user.id
    current_status = user_notifications.get(user_id, False)
    
    kb = InlineKeyboardBuilder()
    
    if current_status:
        kb.button(text="🔕 Выключить уведомления", callback_data="disable_notifications")
        status_text = "✅ включены"
        status_emoji = "🔔"
    else:
        kb.button(text="🔔 Включить уведомления", callback_data="enable_notifications")
        status_text = "🔕 выключены"
        status_emoji = "🔕"
    
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await message.answer(
        f"{status_emoji} *Управление уведомлениями*\n\n"
        f"📊 *Текущий статус:* {status_text}\n\n"
        f"📨 *Вы будете получать:*\n"
        f"• Уведомления о начале матчей\n"
        f"• Результаты избранных команд\n"
        f"• Важные спортивные новости",
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
        "📈 *Статистика игроков*\n\n"
        "👇 Выберите категорию статистики:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# --- ОБРАБОТЧИКИ ЛИГ ---
@dp.callback_query(lambda c: c.data.startswith("league_"))
async def process_league_select(callback: types.CallbackQuery):
    league_key = callback.data.replace("league_", "")
    league_info = POPULAR_LEAGUES.get(league_key)
    
    if not league_info:
        await callback.answer("❌ Лига не найдена")
        return
    
    await callback.answer(f"🔍 Загружаю матчи {league_info['name']}...")
    
    try:
        internal_url = f"http://127.0.0.1:8080/api/internal/matches/league/{league_info['id']}"
        resp = requests.get(internal_url, timeout=10)
        
        if resp.status_code != 200:
            await callback.message.answer("❌ *Ошибка при загрузке матчей лиги*", parse_mode="Markdown")
            return
            
        data = resp.json().get("data", [])
        
        if not data:
            await callback.message.answer(
                f"⚽ *Нет матчей в лиге {league_info['name']}*\n\n"
                f"Попробуйте другую лигу или зайдите позже!",
                parse_mode="Markdown"
            )
            return
            
        await callback.message.answer(
            f"🏆 *Матчи {league_info['emoji']} {league_info['name']}*\n"
            f"📊 Найдено: {len(data)} матчей",
            parse_mode="Markdown"
        )
        
        for m in data[:5]:
            match_text = format_match_message(m)
            await callback.message.answer(match_text, parse_mode="Markdown")
            
    except Exception as e:
        await callback.message.answer("❌ *Ошибка при загрузке матчей лиги*", parse_mode="Markdown")

# --- ОБРАБОТЧИКИ ТУРНИРНЫХ ТАБЛИЦ ---
@dp.callback_query(lambda c: c.data.startswith("table_"))
async def process_table_select(callback: types.CallbackQuery):
    league_key = callback.data.replace("table_", "")
    
    league_names = {
        "premier_league": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Премьер-лига Англия",
        "la_liga": "🇪🇸 Ла Лига Испания",
        "serie_a": "🇮🇹 Серия А Италия", 
        "bundesliga": "🇩🇪 Бундеслига Германия"
    }
    
    league_name = league_names.get(league_key)
    if not league_name:
        await callback.answer("❌ Таблица временно недоступна")
        return
    
    table_data = get_league_table(league_key)
    if not table_data:
        await callback.answer("❌ Данные таблицы недоступны")
        return
    
    table_text = format_table_message(league_name, table_data)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Другие таблицы", callback_data="tables_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(table_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

# --- ОБРАБОТЧИКИ СТАТИСТИКИ ---
@dp.callback_query(lambda c: c.data == "stats_scorers")
async def process_stats_scorers(callback: types.CallbackQuery):
    scorers = get_top_scorers(5)
    stats_text = format_stats_message("scorers", scorers)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(stats_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats_assists")
async def process_stats_assists(callback: types.CallbackQuery):
    assists = get_top_assists(5)
    stats_text = format_stats_message("assists", assists)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(stats_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats_discipline")
async def process_stats_discipline(callback: types.CallbackQuery):
    discipline = get_discipline_stats(5)
    stats_text = format_stats_message("discipline", discipline)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(stats_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats_defense")
async def process_stats_defense(callback: types.CallbackQuery):
    defense = get_defense_stats(5)
    stats_text = format_stats_message("defense", defense)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Другие статистики", callback_data="stats_menu")
    kb.button(text="🔙 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    
    await callback.message.answer(stats_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

# --- ОБРАБОТЧИКИ НАСТРОЕК ---
@dp.callback_query(lambda c: c.data == "enable_notifications")
async def process_enable_notifications(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_notifications[user_id] = True
    await callback.answer("✅ Уведомления включены")
    await callback.message.answer(
        "🔔 *Уведомления включены!*\n\n"
        "Теперь вы будете получать уведомления о:\n"
        "• 📅 Начале матчей\n"
        "• ⭐ Матчах избранных команд\n"
        "• 🎯 Важных спортивных событиях",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "disable_notifications")
async def process_disable_notifications(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_notifications[user_id] = False
    await callback.answer("🔕 Уведомления выключены")
    await callback.message.answer(
        "🔕 *Уведомления выключены*\n\n"
        "Вы больше не будете получать уведомления.\n"
        "Включить их можно в любое время в настройках.",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await callback.answer("🏠 Возвращаюсь в главное меню...")
    await cmd_start(callback.message)

# --- ЗАПУСК БОТА И API ---
def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

async def main():
    # Настройка команд бота
    await set_bot_commands()
    await set_group_commands()
    
    # Запуск API в отдельном потоке
    t_api = threading.Thread(target=run_api, daemon=True)
    t_api.start()
    log.info("🌐 FastAPI запущен на порту 8080")
    
    # Запуск бота
    log.info("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

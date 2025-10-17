import os
import telebot
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Получение токена бота из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.fatal("FATAL: Переменная окружения TELEGRAM_BOT_TOKEN не задана.")
    exit(1)

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)
logger.info("INFO: Бот успешно авторизован.")

# 2. Обработчик команды /start
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    logger.info(f"Received /start from {message.from_user.username}")
    bot.reply_to(message, "Привет! Я бот на Python, запущенный в Kubernetes. Отправь мне любое сообщение!")

# 3. Обработчик всех остальных текстовых сообщений
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    logger.info(f"Received message from {message.from_user.username}: {message.text}")
    # Создаем ответ
    response = "Получено ваше сообщение! Hello, K8s deployment successful! 🚀"
    bot.reply_to(message, response)

# 4. Запуск бота
if __name__ == '__main__':
    logger.info("INFO: Запуск Long Polling.")
    try:
        # Устанавливаем таймаут для Long Polling
        bot.polling(none_stop=True, interval=3) 
    except Exception as e:
        logger.error(f"FATAL ERROR during polling: {e}")

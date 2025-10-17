package main

import (
	"log"
	"os"

	// Убедитесь, что имя локального алиаса (tgbotapi) не изменено
	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	// Получение токена из переменной окружения
	botToken := os.Getenv("TELEGRAM_BOT_TOKEN")
	if botToken == "" {
		// Ошибка, если токен не задан
		log.Fatal("FATAL: Переменная окружения TELEGRAM_BOT_TOKEN не задана.")
	}

	// Инициализация бота
	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		log.Panic(err)
	}

	// НЕ используйте bot.Debug = true, если вы не импортируете пакет debug!
	
	log.Printf("INFO: Авторизован как @%s", bot.Self.UserName)

	// Настройка получения обновлений (Long Polling)
	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	updates := bot.GetUpdatesChan(u)

	// Основной цикл: обработка входящих сообщений
	for update := range updates {
		// Игнорировать, если нет сообщения
		if update.Message == nil {
			continue
		}

		// Логгирование
		log.Printf("[%s] %s", update.Message.From.UserName, update.Message.Text)

		// Создаем и отправляем ответное сообщение
		msg := tgbotapi.NewMessage(update.Message.Chat.ID, "Hello, world! I am running on Kubernetes! 🚀")
		
		if _, err := bot.Send(msg); err != nil {
			log.Println("ERROR: Не удалось отправить сообщение:", err)
		}
	}
}

package main

import (
	"log"
	"os"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	// 1. Получение токена из переменной окружения
	botToken := os.Getenv("TELEGRAM_BOT_TOKEN")
	if botToken == "" {
		log.Fatal("FATAL: Переменная окружения TELEGRAM_BOT_TOKEN не задана.")
	}

	// 2. Инициализация бота
	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		// Используем Panic, так как без бота работать невозможно
		log.Panic(err)
	}

	// Включаем режим отладки (если нужно)
	// bot.Debug = true 

	log.Printf("INFO: Авторизован как @%s", bot.Self.UserName)

	// 3. Настройка получения обновлений (Long Polling)
	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	updates := bot.GetUpdatesChan(u)

	// 4. Основной цикл: обработка входящих сообщений
	for update := range updates {
		// Проверяем, что это сообщение
		if update.Message == nil {
			continue
		}

		// Логгирование входящего сообщения
		log.Printf("[%s] %s", update.Message.From.UserName, update.Message.Text)

		// Создаем ответное сообщение
		msg := tgbotapi.NewMessage(update.Message.Chat.ID, "Hello, world! I am running on Kubernetes! 🚀")
		
		// Отправляем ответ
		if _, err := bot.Send(msg); err != nil {
			log.Println("ERROR: Не удалось отправить сообщение:", err)
		}
	}
}

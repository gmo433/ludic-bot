package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
	// КРИТИЧЕСКАЯ ПРОВЕРКА: Проверяем TELEGRAM_TOKEN
	botToken := os.Getenv("TELEGRAM_TOKEN")
	if botToken == "" {
		// Это должно быть выведено в лог Kubernetes, если токен не подставился
		log.Panic("TELEGRAM_TOKEN environment variable not set or empty")
	}

	// Инициализация бота
	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		// Это будет паника, если токен невалиден
		log.Panic("Failed to create new bot API client: ", err)
	}

	bot.Debug = true // Можно установить в false после отладки
	log.Printf("Authorized on account %s", bot.Self.UserName)

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	updates := bot.GetUpdatesChan(u)

	// Основной цикл обработки обновлений
	for update := range updates {
		if update.Message == nil { // Игнорируем любые не-сообщения
			continue
		}

		if !update.Message.IsCommand() { // Игнорируем не-команды
			continue
		}

		msg := tgbotapi.NewMessage(update.Message.Chat.ID, "")

		switch update.Message.Command() {
		case "start":
			msg.Text = "Привет! Я простой тестовый бот. Используйте /time, чтобы узнать текущее время."
		case "time":
			currentTime := time.Now().Format("15:04:05 MST (2006-01-02)")
			msg.Text = fmt.Sprintf("Текущее время: %s", currentTime)
		default:
			msg.Text = "Неизвестная команда. Попробуйте /time."
		}

		if _, err := bot.Send(msg); err != nil {
			log.Printf("Error sending message: %v", err)
		}
	}
}

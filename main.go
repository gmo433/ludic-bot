package main

import (
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
	"github.com/gmo433/ludic-bot/api"
	"github.com/gmo433/ludic-bot/models" // <-- КРИТИЧЕСКИ ВАЖНЫЙ ИМПОРТ
)

const (
	MatchInterval = 1 * time.Hour 
)

func main() {
	// Токен бота считывается из переменной окружения, переданной K8s Secret
	botToken := os.Getenv("TELEGRAM_BOT_TOKEN") 
	if botToken == "" {
        // Дополнительная проверка на случай, если используется другое имя секрета
        botToken = os.Getenv("TELEGRAM_TOKEN")
        if botToken == "" {
            log.Fatal("TELEGRAM_BOT_TOKEN environment variable not set. Bot cannot start.")
        }
	}

	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		log.Panic(err)
	}

	log.Printf("Authorized on account %s", bot.Self.UserName)

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	updates := bot.GetUpdatesChan(u)

	for update := range updates {
		if update.Message == nil { 
			continue
		}

		if update.Message.IsCommand() {
			switch update.Message.Command() {
			case "start":
				msg := tgbotapi.NewMessage(update.Message.Chat.ID, "Привет! Используй команду /upcoming для получения матчей, которые начнутся в течение часа.")
				bot.Send(msg)
			case "upcoming":
				handleUpcomingMatches(bot, update.Message.Chat.ID)
			default:
				msg := tgbotapi.NewMessage(update.Message.Chat.ID, "Неизвестная команда. Попробуй /upcoming.")
				bot.Send(msg)
			}
		}
	}
}

func handleUpcomingMatches(bot *tgbotapi.BotAPI, chatID int64) {
	log.Printf("Processing /upcoming command for ChatID: %d", chatID)
	
	msg := tgbotapi.NewMessage(chatID, "Ищу матчи, которые начнутся в течение 1 часа...")
	bot.Send(msg)

	// Получаем матчи
	matches, err := api.GetUpcomingMatches(MatchInterval)
	if err != nil {
		log.Printf("Error getting upcoming matches: %v", err)
		errMsg := tgbotapi.NewMessage(chatID, fmt.Sprintf("Произошла ошибка при получении данных: `%v`", err))
		bot.Send(errMsg)
		return
	}

	responseMessage := formatMatches(matches)

	finalMsg := tgbotapi.NewMessage(chatID, responseMessage)
	finalMsg.ParseMode = tgbotapi.ModeMarkdownV2 
	bot.Send(finalMsg)
}

// formatMatches теперь корректно принимает []models.FixtureWrapper
func formatMatches(matches []models.FixtureWrapper) string { 
	if len(matches) == 0 {
		return "В ближайший час матчей не ожидается\\."
	}

	var sb strings.Builder
	sb.WriteString("*⚽️ Предстоящие матчи в течение 1 часа:*\n\n")

	for i, m := range matches {
		// Конвертируем UTC время матча в локальное время для пользователя
		matchTime := m.Fixture.Date.In(time.Local) 
		
		// Экранируем символы Markdown V2: . - ( ) !
		leagueName := strings.ReplaceAll(m.League.Name, ".", "\\.")
		homeTeam := strings.ReplaceAll(m.Teams.Home.Name, "-", "—")
		awayTeam := strings.ReplaceAll(m.Teams.Away.Name, "-", "—")

		sb.WriteString(fmt.Sprintf(
			"*%d\\.* %s: *%s* vs *%s*\n",
			i+1,
			leagueName,
			homeTeam,
			awayTeam,
		))
		sb.WriteString(fmt.Sprintf(
			"  🕒 Начало: `%s` (по времени сервера)\n",
			matchTime.Format("15:04:05 02\\.01"),
		))
		sb.WriteString("\n")
	}

	return sb.String()
}

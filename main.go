package main

import (
	"log"
	"os"
	"fmt"
	"time"
	"net/http"
	"io/ioutil"
	"encoding/json"
	// strings удален отсюда, потому что не использовался

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

// Структуры для декодирования ответа API-FOOTBALL
type Team struct {
	Name string `json:"name"`
}

type Teams struct {
	Home Team `json:"home"`
	Away Team `json:"away"`
}

type Fixture struct {
	Date string `json:"date"` // Дата в формате ISO 8601
}

type MatchDetail struct {
	Fixture Fixture `json:"fixture"`
	Teams   Teams   `json:"teams"`
}

type APIResponse struct {
	Response []MatchDetail `json:"response"`
}

func main() {
	botToken := os.Getenv("TELEGRAM_BOT_TOKEN")
	if botToken == "" {
		log.Panic("TELEGRAM_BOT_TOKEN environment variable not set")
	}

	bot, err := tgbotapi.NewBotAPI(botToken)
	if err != nil {
		log.Panic(err)
	}

	bot.Debug = true
	log.Printf("Authorized on account %s", bot.Self.UserName)

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60

	updates := bot.GetUpdatesChan(u)

	for update := range updates {
		if update.Message != nil {
			handleMessage(bot, update.Message)
		} else if update.CallbackQuery != nil {
			handleCallbackQuery(bot, update.CallbackQuery)
		}
	}
}

func handleMessage(bot *tgbotapi.BotAPI, message *tgbotapi.Message) {
	if !message.IsCommand() {
		return
	}

	msg := tgbotapi.NewMessage(message.Chat.ID, "")

	switch message.Command() {
	case "start":
		msg.Text = "Добро пожаловать! Выберите действие:"
		msg.ReplyMarkup = createMainMenu()
	default:
		msg.Text = "Я не понимаю эту команду."
	}

	if _, err := bot.Send(msg); err != nil {
		log.Println(err)
	}
}

func handleCallbackQuery(bot *tgbotapi.BotAPI, callbackQuery *tgbotapi.CallbackQuery) {
	callback := tgbotapi.NewCallback(callbackQuery.ID, "Обновляю данные...")

	if _, err := bot.Request(callback); err != nil {
		log.Println(err)
	}

	if callbackQuery.Data == "nearest_matches" {
		sendMatches(bot, callbackQuery.Message.Chat.ID)
	}
}

// Создает Inline-кнопки
func createMainMenu() tgbotapi.InlineKeyboardMarkup {
	keyboard := tgbotapi.NewInlineKeyboardMarkup(
		tgbotapi.NewInlineKeyboardRow(
			tgbotapi.NewInlineKeyboardButtonData("⚽ Ближайшие матчи (2ч)", "nearest_matches"),
		),
		tgbotapi.NewInlineKeyboardRow(
			tgbotapi.NewInlineKeyboardButtonURL("Сайт API Football", "https://rapidapi.com/api-sports/api/api-football/"),
		),
	)
	return keyboard
}

// -----------------------------------------------------------------------------------
// ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ МАТЧЕЙ
// ------------------------------------------------

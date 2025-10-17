package main

import (
	"log"
	"os"
	"fmt"
	"time"
	"net/http"
	"io/ioutil"
	"encoding/json"

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
			tgbotapi.NewInlineKeyboardButtonURL("Сайт API Football", "https://dashboard.api-football.com/"),
		),
	)
	return keyboard
}

// -----------------------------------------------------------------------------------
// ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ МАТЧЕЙ (Ультра-упрощенный запрос)
// -----------------------------------------------------------------------------------

func sendMatches(bot *tgbotapi.BotAPI, chatID int64) {
	apiKey := os.Getenv("API_FOOTBALL_KEY")
	if apiKey == "" {
		msg := tgbotapi.NewMessage(chatID, "Ошибка: Ключ API_FOOTBALL_KEY не установлен. Пожалуйста, сообщите администратору.")
		bot.Send(msg)
		return
	}

	// АГРЕССИВНОЕ ИСПРАВЛЕНИЕ: Убираем все параметры (date, league, season)
	// Это должно работать, если только API не требует параметров.
	apiURL := "https://v3.football.api-sport.io/fixtures" 
	
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}
	
	// Используем заголовок X-Api-Key для прямого API
	req.Header.Add("X-Api-Key", apiKey) 
	
	client := http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	
	msgText := ""

	if err != nil {
		log.Printf("Error fetching API: %v", err)
		msgText = "Извините, не удалось подключиться к сервису матчей."
	} else {
		defer resp.Body.Close()
		
		body, _ := ioutil.ReadAll(resp.Body)
		var apiResponse APIResponse
		
		if resp.StatusCode != http.StatusOK {
			log.Printf("API returned status %d. Body: %s", resp.StatusCode, string(body))
			
			// Код 451 теперь ТОЧНО указывает на проблемы с лимитом/подпиской.
			msgText = fmt.Sprintf("Ошибка API: статус %d. Проверьте подписку или лимиты API-Football.", resp.StatusCode)
			
		} else if err := json.Unmarshal(body, &apiResponse); err != nil {
			log.Printf("Error decoding JSON: %v. Body: %s", err, string(body))
			msgText = "Ошибка обработки данных матчей."
		} else {
			msgText = filterAndFormatMatches(apiResponse.Response)
		}
	}
	
	msg := tgbotapi.NewMessage(chatID, msgText)
	msg.ParseMode = "Markdown"
	if _, err := bot.Send(msg); err != nil {
		log.Println(err)
	}
}

// Фильтрует матчи, начинающиеся в ближайшие 2 часа
func filterAndFormatMatches(matches []MatchDetail) string {
	now := time.Now().UTC()
	twoHoursLater := now.Add(2 * time.Hour)
	
	result := "⚽️ *Ближайшие матчи (в течение 2 часов):*\n\n"
	found := false

	// Шаблон времени API-Football: "2006-01-02T15:04:05-07:00"
	const

package main

import (
	"log"
	"os"
	"fmt"
	"time"
	"net/http"
	"io/ioutil"
	"encoding/json"
	"strings"

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
// -----------------------------------------------------------------------------------

func sendMatches(bot *tgbotapi.BotAPI, chatID int64) {
	// 1. Получаем ключ из переменной окружения
	apiKey := os.Getenv("API_FOOTBALL_KEY")
	if apiKey == "" {
		msg := tgbotapi.NewMessage(chatID, "Ошибка: Ключ API_FOOTBALL_KEY не установлен. Пожалуйста, сообщите администратору.")
		bot.Send(msg)
		return
	}

	// 2. Определяем временной диапазон (сегодня). API-FOOTBALL работает по дате.
	today := time.Now().Format("2006-01-02")
	// Пример: запрашиваем фикстуры (матчи) на сегодня для ЛИГИ 39 (Английская Премьер-лига)
	apiURL := fmt.Sprintf("https://api-football-v1.p.rapidapi.com/v3/fixtures?date=%s&league=39&season=2024", today) 
	
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}
	
	// 3. Добавляем необходимые заголовки для RapidAPI
	req.Header.Add("X-RapidAPI-Key", apiKey)
	req.Header.Add("X-RapidAPI-Host", "api-football-v1.p.rapidapi.com")
	
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
			msgText = fmt.Sprintf("Ошибка API: статус %d. Проверьте ключ.", resp.StatusCode)
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

	// Шаблон времени API-Football: "2006-01-02T15:04:05+00:00"
	const apiTimeLayout = "2006-01-02T15:04:05-07:00" 

	for _, match := range matches {
		matchTime, err := time.Parse(apiTimeLayout, match.Fixture.Date)

		if err != nil {
			log.Printf("Error parsing time: %v for date: %s", err, match.Fixture.Date)
			continue
		}
		
		// Фильтруем матчи в диапазоне времени (API возвращает UTC, сравниваем с UTC)
		if matchTime.After(now) && matchTime.Before(twoHoursLater) {
			// Форматируем время для пользователя (например, в московское время)
			localTime := matchTime.In(time.FixedZone("MSK", 3*60*60)) 

			result += fmt.Sprintf("🕔 %s: **%s** vs **%s**\n", 
				localTime.Format("15:04 MSK"), 
				match.Teams.Home.Name, 
				match.Teams.Away.Name)
			found = true
		}
	}

	if !found {
		return "Нет матчей, начинающихся в ближайшие 2 часа."
	}
	return result
}

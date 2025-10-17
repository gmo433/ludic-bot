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

// --- НОВЫЕ СТРУКТУРЫ для API-SPORT.RU ---
type MatchData struct {
	Team1Name string `json:"team1_name"`
	Team2Name string `json:"team2_name"`
	Date string `json:"date"` // Дата и время матча
}

type APISportResponse struct {
	Status string `json:"status"` // Ожидаем "success"
	Data []MatchData `json:"data"`
}
// ----------------------------------------

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
			tgbotapi.NewInlineKeyboardButtonURL("Сайт API Sport", "https://api-sport.ru/"),
		),
	)
	return keyboard
}

// -----------------------------------------------------------------------------------
// ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ МАТЧЕЙ (для API-SPORT.RU)
// -----------------------------------------------------------------------------------

func sendMatches(bot *tgbotapi.BotAPI, chatID int64) {
	apiKey := os.Getenv("API_SPORT_KEY")
	if apiKey == "" {
		msg := tgbotapi.NewMessage(chatID, "Ошибка: Ключ API_SPORT_KEY не установлен. Пожалуйста, сообщите администратору.")
		bot.Send(msg)
		return
	}

	// Формируем URL для получения матчей на сегодня. Используем apikey в URL.
	today := time.Now().Format("2006-01-02")
	apiURL := fmt.Sprintf("https://api-sport.ru/api/matches?date=%s&apikey=%s", today, apiKey) 
	
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}
	
	// Для этого API заголовки не требуются
	client := http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	
	msgText := ""

	if err != nil {
		log.Printf("Error fetching API: %v", err)
		msgText = "Извините, не удалось подключиться к сервису матчей."
	} else {
		defer resp.Body.Close()
		
		body, _ := ioutil.ReadAll(resp.Body)
		var apiResponse APISportResponse
		
		if resp.StatusCode != http.StatusOK {
			log.Printf("API returned status %d. Body: %s", resp.StatusCode, string(body))
			msgText = fmt.Sprintf("Ошибка API: статус %d. Проверьте ваш ключ API Sport.", resp.StatusCode)
			
		} else if err := json.Unmarshal(body, &apiResponse); err != nil {
			log.Printf("Error decoding JSON: %v. Body: %s", err, string(body))
			msgText = "Ошибка обработки данных матчей."
			
		} else if apiResponse.Status != "success" {
			log.Printf("API returned status: %s. Body: %s", apiResponse.Status, string(body))
			msgText = fmt.Sprintf("Ошибка API: статус не 'success'. Проверьте ваш ключ API Sport.")
			
		} else {
			msgText = filterAndFormatMatches(apiResponse.Data)
		}
	}
	
	msg := tgbotapi.NewMessage(chatID, msgText)
	msg.ParseMode = "Markdown"
	if _, err := bot.Send(msg); err != nil {
		log.Println(err)
	}
}

// Фильтрует матчи, начинающиеся в ближайшие 2 часа
func filterAndFormatMatches(matches []MatchData) string {
	now := time.Now().In(time.FixedZone("MSK", 3*60*60)) // Работаем в MSK для нового API
	twoHoursLater := now.Add(2 * time.Hour)
	
	result := "⚽️ *Ближайшие матчи (в течение 2 часов):*\n\n"
	found := false

	// Шаблон времени API-Sport.ru (судя по документации): "YYYY-MM-DD HH:MM:SS"
	const apiTimeLayout = "2006-01-02 15:04:05" 

	for _, match := range matches {
		// Парсим время, предполагая, что оно в MSK (как это часто бывает в российских API)
		matchTime, err := time.ParseInLocation(apiTimeLayout, match.Date, time.FixedZone("MSK", 3*60*60)) 

		if err != nil {
			log.Printf("Error parsing time: %v for date: %s", err, match.Date)
			continue
		}
		
		// Фильтруем матчи в диапазоне времени (сравниваем MSK с MSK)
		if matchTime.After(now) && matchTime.Before(twoHoursLater) {
			result += fmt.Sprintf("🕔 %s: **%s** vs **%s**\n", 
				matchTime.Format("15:04 MSK"), 
				match.Team1Name, 
				match.Team2Name)
			found = true
		}
	}

	if !found {
		return "Нет матчей, начинающихся в ближайшие 2 часа."
	}
	return result
}

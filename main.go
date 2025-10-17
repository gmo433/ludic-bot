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

// --- СТРУКТУРЫ для API-SPORT.RU ---
type MatchData struct {
	Team1Name string `json:"team1_name"`
	Team2Name string `json:"team2_name"`
	Date string `json:"date"` 
}

type APISportResponse struct {
	Status string `json:"status"` 
	Data []MatchData `json:"data"`
}
// ----------------------------------------

// ... (Остальная часть кода main, handleMessage, handleCallbackQuery, createMainMenu) ...

// -----------------------------------------------------------------------------------
// ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ МАТЧЕЙ (для API-SPORT.RU)
// -----------------------------------------------------------------------------------

func sendMatches(bot *tgbotapi.BotAPI, chatID int64) {
	// !!! КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: ИСПОЛЬЗУЕМ ПРАВИЛЬНОЕ ИМЯ API_SPORT_KEY
	apiKey := os.Getenv("API_SPORT_KEY") 
	
	if apiKey == "" {
		// Уточненное сообщение об ошибке
		msg := tgbotapi.NewMessage(chatID, "Ошибка: Ключ API_SPORT_KEY не установлен. Пожалуйста, сообщите администратору.")
		bot.Send(msg)
		return
	}

	// Формируем URL с правильным API-ключом
	today := time.Now().Format("2006-01-02")
	apiURL := fmt.Sprintf("https://api-sport.ru/api/matches?date=%s&apikey=%s", today, apiKey) 
	
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}
	
	client := http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	
	var msgText string

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

// ... (Функция filterAndFormatMatches) ...

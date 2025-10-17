// ... (остальной код main.go) ...

// -----------------------------------------------------------------------------------
// ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ МАТЧЕЙ (ИСПРАВЛЕНА ДЛЯ ПРЯМОГО API-FOOTBALL)
// -----------------------------------------------------------------------------------

func sendMatches(bot *tgbotapi.BotAPI, chatID int64) {
	apiKey := os.Getenv("API_FOOTBALL_KEY")
	if apiKey == "" {
		msg := tgbotapi.NewMessage(chatID, "Ошибка: Ключ API_FOOTBALL_KEY не установлен. Пожалуйста, сообщите администратору.")
		bot.Send(msg)
		return
	}

	today := time.Now().Format("2006-01-02")
	// Используем ПРЯМОЙ URL API-FOOTBALL: v3.football.api-sport.io
	// Используем league=39 (АПЛ) в качестве примера. Если не работает, попробуйте другую лигу или удалите параметры.
	apiURL := fmt.Sprintf("https://v3.football.api-sport.io/fixtures?date=%s&league=39&season=2024", today) 
	
	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return
	}
	
	// !!! ИСПРАВЛЕНИЕ: Используем заголовок X-Api-Key вместо X-RapidAPI-Key !!!
	req.Header.Add("X-Api-Key", apiKey) 
	
	// Заголовок X-RapidAPI-Host БОЛЬШЕ НЕ НУЖЕН
	
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
			// Логируем тело ответа, чтобы увидеть точную причину ошибки
			log.Printf("API returned status %d. Body: %s", resp.StatusCode, string(body))
			
			// Код 451 мог быть вызван неправильными заголовками, но теперь это может быть лимит/подписка.
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

package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/gmo433/ludic-bot/models"
)

const (
	APIBaseURL = "https://v3.football.api-sport.io"
	FixturesEndpoint = "/fixtures"
)

func GetUpcomingMatches(interval time.Duration) ([]models.FixtureWrapper, error) {
	apiKey := os.Getenv("API_FOOTBALL_KEY")
	if apiKey == "" {
		// Это сообщение будет выведено в логах Kubernetes, если секрет не установлен
		return nil, fmt.Errorf("API_FOOTBALL_KEY environment variable not set")
	}

	// 1. Формируем параметры запроса для получения матчей 'Not Started'
	now := time.Now().UTC()
	
	params := url.Values{}
	params.Add("status", "NS") // Not Started
	// !!! КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Убран фильтр по "date", 
	// чтобы избежать ошибки, если интервал переходит через полночь.
	// Фильтрация по времени теперь происходит ТОЛЬКО в коде Go.

	fullURL := fmt.Sprintf("%s%s?%s", APIBaseURL, FixturesEndpoint, params.Encode())

	// 2. Создаем и отправляем HTTP-запрос
	req, err := http.NewRequest("GET", fullURL, nil)
	if err != nil {
		return nil, fmt.Errorf("error creating request: %w", err)
	}
	
	req.Header.Add("x-rapidapi-key", apiKey)
	req.Header.Add("x-rapidapi-host", "v3.football.api-sport.io")

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("error executing request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(resp.Body)
		// Если здесь будет 403 Forbidden, это точно укажет на невалидный API_FOOTBALL_KEY!
		return nil, fmt.Errorf("API request failed with status code %d: %s", resp.StatusCode, string(bodyBytes))
	}

	// 3. Парсим ответ
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("error reading response body: %w", err)
	}

	var apiResponse models.FootballAPIResponse
	if err := json.Unmarshal(body, &apiResponse); err != nil {
		return nil, fmt.Errorf("error unmarshalling response: %w", err)
	}

	// 4. Фильтрация матчей по времени (в пределах заданного интервала)
	var upcomingMatches []models.FixtureWrapper
	targetTime := now.Add(interval) // Определяем верхний предел (текущее время + интервал)
	
	for _, wrapper := range apiResponse.Response {
		matchTime := wrapper.Fixture.Date
		
		// Фильтруем: матч должен быть после текущего момента (now) и до целевого времени (targetTime)
		if matchTime.After(now) && matchTime.Before(targetTime) {
			upcomingMatches = append(upcomingMatches, wrapper)
		}
	}
	
	return upcomingMatches, nil
}

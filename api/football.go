package api

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/gmo433/ludic-bot/models" // <--- ОБНОВЛЕНО
)

const (
	APIBaseURL = "https://v3.football.api-sport.io"
	FixturesEndpoint = "/fixtures"
)

func GetUpcomingMatches(interval time.Duration) ([]models.FixtureWrapper, error) {
	apiKey := os.Getenv("API_FOOTBALL_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("API_FOOTBALL_KEY environment variable not set")
	}

	// 1. Формируем параметры запроса для получения матчей 'Not Started'
	now := time.Now().UTC()
	from := now.Format("2006-01-02")

	params := url.Values{}
	params.Add("status", "NS") // Not Started
	params.Add("date", from) 

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

	// 4. Фильтрация матчей по времени (в пределах 1 часа)
	var upcomingMatches []models.FixtureWrapper
	targetTime := now.Add(interval) 
	
	for _, wrapper := range apiResponse.Response {
		// Время в API всегда UTC. Сравниваем с UTC временем 'now'.
		matchTime := wrapper.Fixture.Date 
		
		if matchTime.After(now) && matchTime.Before(targetTime) {
			upcomingMatches = append(upcomingMatches, wrapper)
		}
	}
	
	return upcomingMatches, nil
}

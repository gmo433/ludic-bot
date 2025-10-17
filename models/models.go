package models

import "time"

// FootballAPIResponse представляет верхний уровень ответа API-Football
type FootballAPIResponse struct {
	Response []FixtureWrapper `json:"response"`
}

// FixtureWrapper оборачивает информацию о матче
type FixtureWrapper struct {
	Fixture FixtureDetails `json:"fixture"`
	League  LeagueDetails  `json:"league"`
	Teams   TeamDetails    `json:"teams"`
}

// FixtureDetails содержит основные данные о матче
type FixtureDetails struct {
	ID        int       `json:"id"`
	Date      time.Time `json:"date"` // API обычно возвращает дату в формате ISO, Go умеет парсить
	Timezone  string    `json:"timezone"`
	Timestamp int64     `json:"timestamp"`
	Status    Status    `json:"status"`
}

// Status содержит информацию о статусе матча
type Status struct {
	Short string `json:"short"` // Например, "TBD", "NS" (Not Started)
}

// TeamDetails содержит информацию о командах
type TeamDetails struct {
	Home Team `json:"home"`
	Away Team `json:"away"`
}

// Team содержит детали о конкретной команде
type Team struct {
	Name string `json:"name"`
	Logo string `json:"logo"`
}

// LeagueDetails содержит детали о лиге
type LeagueDetails struct {
	Name string `json:"name"`
}

package matches

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"time"
)

type fixtureResponse struct {
	Response []struct {
		Fixture struct {
			Timestamp int64 `json:"timestamp"`
		} `json:"fixture"`
		Teams struct {
			Home struct{ Name string } `json:"home"`
			Away struct{ Name string } `json:"away"`
		} `json:"teams"`
		League struct {
			Name string `json:"name"`
		} `json:"league"`
	} `json:"response"`
}

type Match struct {
	HomeTeam  string
	AwayTeam  string
	StartTime time.Time
	League    string
	Notified  bool
}

func FetchUpcomingMatches(hoursAhead int) ([]Match, error) {
	apiKey := os.Getenv("API_FOOTBALL_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("API_FOOTBALL_KEY not set")
	}

	now := time.Now().UTC()
	end := now.Add(time.Duration(hoursAhead) * time.Hour)
	dates := uniqueDates(now, end)

	var matches []Match
	client := &http.Client{Timeout: 10 * time.Second}

	for _, d := range dates {
		url := fmt.Sprintf("https://v3.football.api-sports.io/fixtures?date=%s&status=NS", d.Format("2006-01-02"))
		req, _ := http.NewRequest("GET", url, nil)
		req.Header.Add("x-apisports-key", apiKey)

		resp, err := client.Do(req)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()

		var fr fixtureResponse
		if err := json.NewDecoder(resp.Body).Decode(&fr); err != nil {
			return nil, err
		}

		for _, r := range fr.Response {
			start := time.Unix(r.Fixture.Timestamp, 0).UTC()
			if start.After(now) && start.Before(end) {
				matches = append(matches, Match{
					HomeTeam:  r.Teams.Home.Name,
					AwayTeam:  r.Teams.Away.Name,
					StartTime: start,
					League:    r.League.Name,
					Notified:  false,
				})
			}
		}
	}

	return matches, nil
}

func uniqueDates(from, to time.Time) []time.Time {
	var days []time.Time
	cur := time.Date(from.Year(), from.Month(), from.Day(), 0, 0, 0, 0, time.UTC)
	endDate := time.Date(to.Year(), to.Month(), to.Day(), 0, 0, 0, 0, time.UTC)
	for !cur.After(endDate) {
		days = append(days, cur)
		cur = cur.Add(24 * time.Hour)
	}
	return days
}

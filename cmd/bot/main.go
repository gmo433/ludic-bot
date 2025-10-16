package main

import (
	"log"
	"os"
	"sync"
	"time"

	tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
	"github.com/<твой_ник>/ludic-bot/internal/db"
	"github.com/<твой_ник>/ludic-bot/internal/matches"
)

const (
	notifyBefore  = 15 * time.Minute
	fetchInterval = 5 * time.Minute
	hoursAhead    = 24
)

func main() {
	if err := db.Connect(); err != nil {
		log.Fatalf("❌ DB connect error: %v", err)
	}
	defer db.Close()

	teleToken := os.Getenv("TELEGRAM_TOKEN")
	if teleToken == "" {
		log.Fatal("TELEGRAM_TOKEN not set")
	}

	bot, err := tgbotapi.NewBotAPI(teleToken)
	if err != nil {
		log.Panic(err)
	}

	log.Printf("Bot authorized: %s", bot.Self.UserName)

	var mu sync.Mutex
	var upcoming []matches.Match

	// Загружаем пользователей из БД
	users, _ := db.GetAllUsers()
	userChats := make(map[int64]bool)
	for _, u := range users {
		userChats[u.ChatID] = true
	}
	log.Printf("📋 Loaded %d subscribers", len(userChats))

	// Гор. обновления матчей
	go func() {
		for {
			list, err := matches.FetchUpcomingMatches(hoursAhead)
			if err != nil {
				log.Printf("[fetch] %v", err)
			} else {
				mu.Lock()
				upcoming = list
				mu.Unlock()
			}
			time.Sleep(fetchInterval)
		}
	}()

	// Гор. уведомлений
	go func() {
		for {
			mu.Lock()
			now := time.Now().UTC()
			for i := range upcoming {
				m := &upcoming[i]
				if m.Notified {
					continue
				}
				diff := m.StartTime.Sub(now)
				if diff <= notifyBefore && diff > 0 {
					text := "⚽ Через 15 минут матч:\n" +
						m.HomeTeam + " 🆚 " + m.AwayTeam + "\n" +
						"Лига: " + m.League + "\n" +
						"UTC: " + m.StartTime.Format("15:04")
					for chatID := range userChats {
						_, err := bot.Send(tgbotapi.NewMessage(chatID, text))
						if err != nil {
							log.Printf("Send error: %v", err)
						}
					}
					m.Notified = true
				}
			}
			mu.Unlock()
			time.Sleep(time.Minute)
		}
	}()

	u := tgbotapi.NewUpdate(0)
	u.Timeout = 60
	updates := bot.GetUpdatesChan(u)

	for upd := range updates {
		if upd.Message == nil {
			continue
		}
		switch upd.Message.Command() {
		case "start":
			mu.Lock()
			userChats[upd.Message.Chat.ID] = true
			mu.Unlock()
			db.AddUser(upd.Message.Chat.ID, upd.Message.From.UserName)
			bot.Send(tgbotapi.NewMessage(upd.Message.Chat.ID,
				"Привет! Я уведомлю тебя за 15 мин до матча ⚽"))
		case "stop":
			mu.Lock()
			delete(userChats, upd.Message.Chat.ID)
			mu.Unlock()
			db.RemoveUser(upd.Message.Chat.ID)
			bot.Send(tgbotapi.NewMessage(upd.Message.Chat.ID, "Оповещения отключены."))
		case "list":
			mu.Lock()
			list := upcoming
			mu.Unlock()
			if len(list) == 0 {
				bot.Send(tgbotapi.NewMessage(upd.Message.Chat.ID, "Нет предстоящих матчей."))
			} else {
				for _, m := range list {
					line := m.HomeTeam + " vs " + m.AwayTeam + " — " + m.StartTime.Format("2006-01-02 15:04") + " UTC"
					bot.Send(tgbotapi.NewMessage(upd.Message.Chat.ID, line))
				}
			}
		}
	}
}

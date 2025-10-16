package main

import (
    "fmt"
    "log"
    "os"

    "github.com/gmo433/ludic-bot/internal/db"
    "github.com/gmo433/ludic-bot/internal/matches"
    tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
    token := os.Getenv("TELEGRAM_TOKEN")
    if token == "" {
        log.Fatal("TELEGRAM_TOKEN is not set")
    }

    bot, err := tgbotapi.NewBotAPI(token)
    if err != nil {
        log.Panic(err)
    }

    fmt.Println("Bot started:", bot.Self.UserName)

    // Здесь будет логика анализа матчей
    _ = db.Connect()
    _ = matches.FetchUpcomingMatches()
}

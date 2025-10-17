package main

import (
    "log"
    "os"

    tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

func main() {
    // 1. Получение токена бота из переменных окружения
    botToken := os.Getenv("TELEGRAM_BOT_TOKEN")
    if botToken == "" {
        log.Fatal("Ошибка: Переменная окружения TELEGRAM_BOT_TOKEN не задана.")
    }

    // 2. Создание нового экземпляра бота
    bot, err := tgbotapi.NewBotAPI(botToken)
    if err != nil {
        log.Panic(err)
    }

    // Опционально: включение режима отладки
    // bot.Debug = true // <-- ВОЗМОЖНО, ПРОБЛЕМА ЗДЕСЬ!

    log.Printf("Авторизован как @%s", bot.Self.UserName)

    // 3. Настройка получения обновлений (апдейтов)
    u := tgbotapi.NewUpdate(0)
    u.Timeout = 60 // Таймаут для long polling

    updates := bot.GetUpdatesChan(u)

    // 4. Основной цикл обработки сообщений
    for update := range updates {
        // Пропускаем обновления, которые не являются сообщениями
        if update.Message == nil {
            continue
        }

        log.Printf("[%s] %s", update.Message.From.UserName, update.Message.Text)

        // Создаем новое сообщение для отправки в тот же чат
        msg := tgbotapi.NewMessage(update.Message.Chat.ID, "Hello, world! 🌍")

        // Отправляем сообщение
        if _, err := bot.Send(msg); err != nil {
            log.Println("Ошибка отправки сообщения:", err)
        }
    }
}

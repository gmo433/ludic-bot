# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем go.mod
COPY go.mod .

# 2. Устойчивость: Принудительно загружаем и чистим зависимости
RUN go mod tidy 

# 3. Копируем весь исходный код (включая main.go)
COPY . .

# 4. !!! ДИАГНОСТИКА: Выводим содержимое файла main.go !!!
# Ищите здесь невидимые символы или лишние строки.
RUN echo "--- START MAIN.GO CONTENT ---" && cat main.go && echo "--- END MAIN.GO CONTENT ---"

# 5. !!! ДИАГНОСТИКА: Проверяем наличие файла main.go в WORKDIR !!!
RUN ls -l

# 6. Сборка исполняемого файла
# Если все выше работает, эта команда должна пройти
RUN CGO_ENABLED=0 go build -v -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /bot .

# Запуск бота
CMD ["./bot"]

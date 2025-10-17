# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем только go.mod для кэширования зависимостей
COPY go.mod .

# 2. Загружаем зависимости (автоматически создает go.sum внутри контейнера)
RUN go mod download

# 3. !!! КРИТИЧЕСКИ ВАЖНО: Копируем весь исходный код (включая main.go) !!!
# КОНТЕКСТ '.' (репозиторий) -> КУДА КОПИРОВАТЬ '.' (/app в контейнере)
COPY . .

# 4. Сборка статического исполняемого файла
# Теперь main.go точно находится в /app, и команда должна сработать
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
# Установка сертификатов для HTTPS-запросов
RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /bot .
CMD ["./bot"]

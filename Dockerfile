# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем go.mod
COPY go.mod .

# 2. Загружаем зависимости
RUN go mod download

# 3. Копируем весь исходный код (main.go)
COPY . .

# 4. !!! ФИНАЛЬНОЕ ИЗМЕНЕНИЕ: Используем go build с явными путями !!!
# Сборка пакета main в текущей директории (./) и сохранение его в /bot.
RUN CGO_ENABLED=0 go build -v -ldflags "-s -w" -o /bot .

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
# Установка сертификатов для HTTPS-запросов
RUN apk --no-cache add ca-certificates

WORKDIR /root/
# Копирование исполняемого файла из стадии сборки
COPY --from=builder /bot .

# Запуск бота
CMD ["./bot"]

# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем только go.mod (и go.sum, если он есть)
# Это нужно для кэширования Docker слоев.
COPY go.mod go.sum ./

# 2. Загружаем зависимости (автоматически создает/обновляет go.sum внутри контейнера)
RUN go mod download

# 3. !!! ВАЖНО: Копируем весь исходный код (включая main.go) !!!
# Точка '.' означает "скопировать все из текущего контекста"
COPY . .

# 4. Сборка статического исполняемого файла
# Если main.go находится в WORKDIR /app, то эта команда сработает.
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
# Установка сертификатов для HTTPS-запросов
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Копирование исполняемого файла из стадии сборки
COPY --from=builder /bot .

# Запуск бота
CMD ["./bot"]

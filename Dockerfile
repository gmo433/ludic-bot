# Dockerfile
# --- СТАДИЯ СБОРКИ ---
# !!! МЕНЯЕМ БАЗОВЫЙ ОБРАЗ С ALPINE НА DEBIAN-SLIM !!!
FROM golang:1.21-slim AS builder

WORKDIR /app

# 1. Копируем go.mod
COPY go.mod .

# 2. Устойчивость: Принудительно загружаем и чистим зависимости
RUN go mod tidy 

# 3. Копируем весь исходный код (включая main.go)
COPY . .

# 4. Сборка исполняемого файла
# Команда, которая должна работать
RUN CGO_ENABLED=0 go build -v -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
# !!! МЕНЯЕМ ФИНАЛЬНЫЙ ОБРАЗ НА DEBIAN-SLIM ДЛЯ СООТВЕТСТВИЯ !!!
FROM debian:buster-slim
# Здесь не нужны ca-certificates, так как они уже есть в образе debian-slim

WORKDIR /root/
# Копирование исполняемого файла
COPY --from=builder /bot .

# Запуск бота
CMD ["./bot"]

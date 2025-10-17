# Dockerfile
# --- СТАДИЯ СБОРКИ (остается без изменений) ---
FROM golang:1.21 AS builder

WORKDIR /app
COPY go.mod .
RUN go mod tidy 
COPY . .
RUN CGO_ENABLED=0 go build -v -ldflags "-s -w" -o /bot .

# --- ФИНАЛЬНЫЙ ОБРАЗ (Исправлена последовательность) ---
FROM debian:buster-slim

WORKDIR /root/
# 1. КОПИРОВАНИЕ: Сначала копируем файл 'bot' в /root/
COPY --from=builder /bot .

# 2. CHMOD: Теперь, когда файл существует, мы можем изменить его права доступа
RUN chmod +x /root/bot

# Запуск бота
CMD ["./bot"]

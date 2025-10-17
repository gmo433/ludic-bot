FROM golang:1.21-alpine AS builder

WORKDIR /app

# Копируем все файлы (main.go, go.mod)
COPY . .

# !!! АГРЕССИВНОЕ ИСПРАВЛЕНИЕ: Объединяем скачивание, создание go.sum и сборку в один шаг !!!
RUN go mod download && \
    go mod tidy && \
    CGO_ENABLED=0 go build -ldflags "-s -w" -o /hello-bot .

# Этап 2: Финальный образ
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /hello-bot .

ENV TELEGRAM_BOT_TOKEN="" 

CMD ["./hello-bot"]

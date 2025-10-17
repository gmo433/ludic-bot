FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем все файлы (main.go, go.mod)
COPY . .

# 2. Скачиваем зависимости. Это создаст/обновит go.sum.
RUN go mod download 

# 3. Сборка статического бинарника.
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /hello-bot .

# Этап 2: Финальный образ
FROM alpine:latest

# Устанавливаем сертификаты
RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /hello-bot .

# !!! ИСПРАВЛЕНО: Удалили комментарий из этой строки !!!
ENV TELEGRAM_BOT_TOKEN="" 

CMD ["./hello-bot"]

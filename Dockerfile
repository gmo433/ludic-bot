# Этап 1: Сборка
FROM golang:1.21-alpine AS builder

WORKDIR /app
# Копируем go.mod и go.sum (созданы вручную)
COPY go.mod go.sum ./
# Эта команда сама скачает зависимости на этапе сборки Docker
RUN go mod download 

COPY . .

# Сборка статического бинарника
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /hello-bot .

# Этап 2: Финальный образ (минимальный)
FROM alpine:latest

# Устанавливаем сертификаты для HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /root/
# Копируем бинарник 
COPY --from=builder /hello-bot .

# Переменная окружения для токена (будет задана K8s)
ENV TELEGRAM_BOT_TOKEN=""

# Запуск приложения
CMD ["./hello-bot"]

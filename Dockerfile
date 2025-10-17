# Этап 1: Сборка
FROM golang:1.21-alpine AS builder

WORKDIR /app
# Копируем только go.mod
COPY go.mod ./ 

# СКАЧИВАЕМ ЗАВИСИМОСТИ И ОБНОВЛЯЕМ GO.SUM ВМЕСТЕ
# Это гарантирует, что go.mod и go.sum актуальны перед копированием кода
RUN go mod download

# Копируем остальной код, включая main.go
COPY . .

# Сборка статического бинарника
# Go Build теперь видит сгенерированный go.sum из предыдущего шага
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

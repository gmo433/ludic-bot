# Использование многоступенчатой сборки для создания минимального образа
# Стадия сборки
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Копирование go.mod и go.sum для кэширования зависимостей
COPY go.mod go.sum ./
RUN go mod download

# Копирование исходного кода
COPY . .

# Сборка статического исполняемого файла
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /bot main.go

# Финальный образ (минимальный)
FROM alpine:latest
# Установка сертификатов для HTTPS-запросов
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Копирование исполняемого файла из стадии сборки
COPY --from=builder /bot .

# Запуск бота
CMD ["./bot"]

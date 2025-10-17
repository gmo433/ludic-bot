# Этап 1: Сборка
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Копируем go.mod и go.sum, чтобы кэшировать зависимости
COPY go.mod go.sum ./
RUN go mod download

# Копируем исходный код
COPY . .

# Компилируем статический бинарник
RUN CGO_ENABLED=0 go build -a -tags netgo -ldflags "-s -w" -o football-bot .

# Этап 2: Итоговый образ (минимальный)
FROM alpine:latest

# Устанавливаем часовой пояс
RUN apk --no-cache add tzdata

WORKDIR /root/

# Копируем скомпилированный бинарник
COPY --from=builder /app/football-bot .

# Копируем информацию о часовых поясах (необходимо для time.Local в Go)
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Команда для запуска
CMD ["./football-bot"]

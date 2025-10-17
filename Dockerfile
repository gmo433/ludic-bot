# Этап 1: Сборка
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем все файлы, включая go.mod и main.go
COPY . .

# 2. Скачиваем зависимости. Это создаст/обновит go.sum
# и поместит все в кэш модулей, доступный для следующего шага.
RUN go mod download 

# 3. Сборка статического бинарника.
# Теперь go build имеет доступ ко всем файлам и кэшу модулей.
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /hello-bot .

# Этап 2: Финальный образ (минимальный)
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /hello-bot .

ENV TELEGRAM_BOT_TOKEN="" # (ВНИМАНИЕ: это предупреждение об использовании ENV для секрета игнорируем, т.к. K8s использует эту ENV)

CMD ["./hello-bot"]

# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем только go.mod
COPY go.mod .

# 2. Загружаем зависимости
RUN go mod download

# 3. Копируем весь исходный код
COPY . .

# 4. Сборка исполняемого файла
# УДАЛЯЕМ -s -w и добавляем -v для подробного вывода
RUN CGO_ENABLED=0 go build -v -o /bot main.go 
#                               ^--- Добавлено -v

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /bot .
CMD ["./bot"]

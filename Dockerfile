# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем go.mod
COPY go.mod .

# 2. Устойчивость: Принудительно загружаем и чистим зависимости
RUN go mod tidy 

# 3. Копируем весь исходный код (включая main.go)
COPY . .

# 4. Сборка исполняемого файла
# Явное указание файла 'main.go' - самый чистый способ.
RUN CGO_ENABLED=0 go build -v -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /bot .

# Запуск бота
CMD ["./bot"]

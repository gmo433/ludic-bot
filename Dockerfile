# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем ТОЛЬКО go.mod. (Удаляем упоминание go.sum, чтобы избежать ошибки "not found")
# Этот шаг копирует только один существующий файл, что позволяет ему работать без go.sum
COPY go.mod .

# 2. Загружаем зависимости. Это автоматически создаст go.sum внутри контейнера.
# Docker не будет использовать кэш для этого RUN, если изменился go.mod.
RUN go mod download

# 3. Копируем весь исходный код (включая main.go)
COPY . .

# 4. Сборка исполняемого файла
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
RUN apk --no-cache add ca-certificates

WORKDIR /root/
COPY --from=builder /bot .
CMD ["./bot"]

# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

WORKDIR /app

# 1. Копируем go.mod
COPY go.mod .

# 2. !!! Устойчивость: Принудительно запускаем go mod tidy для гарантии go.sum и загрузки !!!
# Это устраняет любые невидимые проблемы с зависимостями.
RUN go mod tidy 

# 3. Копируем весь исходный код (включая main.go)
COPY . .

# 4. !!! ОКОНЧАТЕЛЬНОЕ ИЗМЕНЕНИЕ: go build с явным именем файла main.go !!!
# Это самый надежный способ сборки: указать точный файл.
RUN CGO_ENABLED=0 go build -v -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
# Установка сертификатов для HTTPS-запросов
RUN apk --no-cache add ca-certificates

WORKDIR /root/
# Копирование исполняемого файла из стадии сборки
COPY --from=builder /bot .

# Запуск бота
CMD ["./bot"]

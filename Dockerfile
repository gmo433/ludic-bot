# ----------------------------------------------------
# Этап 1: Builder - Сборка Go-приложения
# ----------------------------------------------------
FROM golang:1.22-alpine AS builder

# 1. Устанавливаем рабочую директорию
WORKDIR /app

# 2. КОПИРУЕМ ФАЙЛЫ МОДУЛЯ: go.mod и go.sum
COPY go.mod go.sum ./
RUN go mod download

# 3. КОПИРУЕМ ВЕСЬ ОСТАЛЬНОЙ ИСХОДНЫЙ КОД (main.go, api/, models/)
COPY . .

# 4. Компилируем статический бинарник (Здесь происходит ошибка!)
RUN CGO_ENABLED=0 go build -a -tags netgo -ldflags "-s -w" -o football-bot .

# ... (Остальная часть Dockerfile)

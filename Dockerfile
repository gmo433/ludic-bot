# ----------------------------------------------------
# Этап 1: Builder - Сборка Go-приложения
# ----------------------------------------------------
FROM golang:1.22-alpine AS builder

WORKDIR /app

# 1. Копируем go.mod и go.sum и загружаем то, что известно
COPY go.mod go.sum ./
RUN go mod download

# 2. КОПИРУЕМ ВЕСЬ ИСХОДНЫЙ КОД
COPY . .

# 3. КРИТИЧЕСКИЙ ШАГ: Убеждаемся, что go.mod и go.sum соответствуют
#    новым импортам в скопированном коде. Это решает проблему "missing go.sum entry".
RUN go mod tidy

# 4. Компилируем статический бинарник
RUN CGO_ENABLED=0 go build -a -tags netgo -ldflags "-s -w" -o football-bot .

# ... (Остальная часть Dockerfile)

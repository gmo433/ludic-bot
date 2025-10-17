# Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Шаг 1: Копируем ТОЛЬКО go.mod
COPY go.mod .

# Шаг 2: Загружаем зависимости. Это автоматически создает go.sum внутри контейнера.
RUN go mod download

# Шаг 3: Теперь копируем остальной код (main.go)
COPY . .

# Сборка статического исполняемого файла
RUN CGO_ENABLED=0 go build -ldflags "-s -w" -o /bot main.go

# ... (Остальная часть финального образа)

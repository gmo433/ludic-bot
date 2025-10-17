# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21 AS builder

WORKDIR /app

# 1. Копируем только main.go (гарантируем его присутствие)
COPY main.go .

# 2. Копируем go.mod
COPY go.mod .

# 3. Загружаем и очищаем зависимости (генерирует go.sum)
RUN go mod tidy 

# 4. Копируем все остальные файлы (если они есть)
COPY . .

# 5. Сборка исполняемого файла
# Используем go build main.go — самый надёжный способ, когда main.go находится в WORKDIR.
RUN CGO_ENABLED=0 go build -v -ldflags "-s -w" -o /bot main.go

# --- ФИНАЛЬНЫЙ ОБРАЗ (Минимальный) ---
FROM debian:buster-slim

WORKDIR /root/

# 6. Копируем исполняемый файл из стадии сборки
COPY --from=builder /bot .

# 7. Убеждаемся, что бинарник имеет права на исполнение
RUN chmod +x /root/bot

# Запуск бота
CMD ["./bot"]

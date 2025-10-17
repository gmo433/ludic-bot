# Dockerfile
# --- СТАДИЯ СБОРКИ ---
FROM golang:1.21-alpine AS builder

# Устанавливаем GOPATH и GOBIN (путь для исполняемых файлов)
ENV GOPATH /go
ENV GOBIN /go/bin

WORKDIR /app

# 1. Копируем go.mod
COPY go.mod .

# 2. Загружаем зависимости
RUN go mod download

# 3. Копируем весь исходный код (включая main.go)
COPY . .

# 4. !!! КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Используем go install ./... !!!
# CGO_ENABLED=0 и go install соберут статический бинарник и поместят его в $GOBIN.
# Мы явно указываем, что исполняемый файл будет называться 'bot'
RUN CGO_ENABLED=0 go install -v -ldflags "-s -w" -o ${GOBIN}/bot ./...

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
FROM alpine:latest
# Установка сертификатов для HTTPS-запросов
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Копирование исполняемого файла из $GOBIN стадии сборки
COPY --from=builder ${GOBIN}/bot .

# Запуск бота
CMD ["./bot"]

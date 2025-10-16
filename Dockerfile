# Stage 1: Build
FROM golang:1.22.2-alpine AS build
WORKDIR /app

# Копируем go.mod и go.sum
COPY go.mod go.sum ./
RUN go mod download

# Копируем весь код
COPY . .

# Собираем бинарь
RUN go build -o ludic-bot ./cmd/bot

# Stage 2: Runtime
FROM alpine:3.18
WORKDIR /app

# Копируем бинарь из сборочного этапа
COPY --from=build /app/ludic-bot .

ENV TELEGRAM_TOKEN=""
ENV API_FOOTBALL_KEY=""
ENV DATABASE_URL=""

CMD ["./ludic-bot"]

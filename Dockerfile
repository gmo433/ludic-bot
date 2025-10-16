# Stage 1: build
FROM golang:1.22.2-alpine AS build
WORKDIR /app

# Секреты передаются через build-args
ARG API_FOOTBALL_KEY
ARG TELEGRAM_TOKEN
ENV API_FOOTBALL_KEY=$API_FOOTBALL_KEY
ENV TELEGRAM_TOKEN=$TELEGRAM_TOKEN

# Копируем зависимости
COPY go.mod go.sum ./
RUN go mod download

# Копируем весь проект
COPY . .

# Сборка
RUN go build -o ludic-bot ./cmd/bot

# Stage 2: final image
FROM alpine:3.18
WORKDIR /app
COPY --from=build /app/ludic-bot .
CMD ["./ludic-bot"]

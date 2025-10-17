FROM golang:1.22-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o ludic-bot cmd/bot/main.go

FROM alpine:3.18
WORKDIR /app
COPY --from=build /app/ludic-bot .
CMD ["./ludic-bot"]

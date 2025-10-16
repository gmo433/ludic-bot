FROM golang:1.20-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /usr/local/bin/ludic-bot ./cmd/bot

FROM alpine:3.18
COPY --from=build /usr/local/bin/ludic-bot /usr/local/bin/ludic-bot
ENV TZ=UTC
CMD ["/usr/local/bin/ludic-bot"]

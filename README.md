# Ludic Bot

Telegram bot + Mini App that shows upcoming football matches (next 2 hours) on demand.

## Features
- Aiogram-based Telegram bot
- Mini‑app (Telegram Web App) UI served by FastAPI
- `/matches` command supported (bot replies with matches)
- CI/CD via GitHub Actions: builds Docker image and pushes to Docker Hub (`roman3327/ludic-bot:latest`), then deploys to Kubernetes using `KUBECONFIG_B64` secret.

## Secrets to add in GitHub
- `DOCKERHUB_USERNAME` — your Docker Hub username
- `DOCKERHUB_PASSWORD` — Docker Hub password or token
- `KUBECONFIG_B64` — base64-encoded kubeconfig for target cluster
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `API_SPORT_KEY` — API-Sport key

## How it works
1. Push to `main` branch -> GitHub Actions builds image and pushes to Docker Hub.
2. Action decodes `KUBECONFIG_B64` and applies Kubernetes manifests in `k8s/`.
3. Service is of type LoadBalancer — once provisioned you'll get a public IP. Set `WEBAPP_URL` env var in deployment to `http(s)://<PUBLIC_IP>` so Telegram mini-app opens correctly.

## Local testing
- Set env vars `TELEGRAM_BOT_TOKEN` and `API_SPORT_KEY`.
- Run `python app/main.py` and visit `http://localhost:8080/` (for webapp).
- Note: For Telegram WebApp to work, Telegram requires an HTTPS URL accessible from the internet.


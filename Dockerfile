# --- STAGE 1: BUILD (Сборка) ---
# Используем более полный образ для сборки, чтобы установить зависимости C/C++
FROM python:3.11-slim AS builder

# Устанавливаем системные зависимости, необходимые для компиляции Python-пакетов
# (Например, для psycopg2, cryptography, lxml)
# build-essential, gcc, libpq-dev
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем только requirements для использования кеша Docker
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# --- STAGE 2: FINAL (Финальный образ) ---
# Используем минимальный образ, чтобы сделать его легким и безопасным
FROM python:3.11-slim

# Устанавливаем только библиотеки времени выполнения (Runtime libraries)
# libpq5 нужна, если вы используете PostgreSQL
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем установленные зависимости из 'builder'
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Копируем код приложения (папка app/ должна находиться в корне репозитория)
COPY app /app/

# Настройка переменных окружения
ENV PYTHONUNBUFFERED 1
ENV UVICORN_PORT 8080

EXPOSE 8080

# Команда запуска FastAPI/Uvicorn
# 'main' - это имя вашего файла (main.py)
# 'app' - это имя экземпляра FastAPI в main.py (app = FastAPI(...))
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

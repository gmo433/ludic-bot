# Dockerfile
# --- СТАДИЯ СБОРКИ ---
# Используем образ Python, основанный на Debian Buster (более стабильный, чем Alpine для Python)
FROM python:3.11-slim-buster AS builder

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY main.py .

# --- ФИНАЛЬНЫЙ ОБРАЗ ---
# Используем минимальный образ без SDK для уменьшения размера
FROM python:3.11-slim-buster

# Устанавливаем рабочую директорию и копируем зависимости из стадии builder
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код приложения (main.py)
COPY main.py .

# Команда для запуска бота
CMD ["python", "main.py"]

# ==========================
# ✅ Рабочий Dockerfile для ludic-bot
# ==========================
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Обновляем системные пакеты (для сертификатов HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# ✅ Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Копируем исходный код бота
COPY bot.py .

# Отключаем буферизацию stdout/stderr, чтобы логи сразу шли в kubectl logs
ENV PYTHONUNBUFFERED=1

# Запускаем бота
CMD ["python", "bot.py"]

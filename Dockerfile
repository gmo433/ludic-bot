# ==========================
# ✅ Рабочий Dockerfile для ludic-bot
# ==========================
FROM python:3.11-slim

WORKDIR /app

# Обновляем систему и ставим минимальные зависимости (для сборки wheel'ов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Копируем список зависимостей
COPY requirements.txt .

# ✅ Обновляем pip, setuptools и wheel перед установкой
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]

FROM python:3.11-slim

WORKDIR /app

# Системные зависимости для сборки Python пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]

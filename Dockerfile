FROM python:3.11-slim

WORKDIR /app

# Устанавливаем все системные зависимости для сборки пакетов с C-расширениями
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .

# Обновляем pip, setuptools, wheel и ставим зависимости
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]

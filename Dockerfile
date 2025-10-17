# --- STAGE 1: BUILD (Сборка) ---# --- STAGE 1: BUILDER (Сборка) ---
# Используем полный образ Python для установки системных зависимостей и компиляции
FROM python:3.11 as builder

# Устанавливаем системные пакеты, необходимые для компиляции 
# (например, для psycopg2, cryptography, lxml и других, требующих C-компилятор)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочий каталог
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Установка Python-зависимостей (теперь она должна работать)
RUN pip install --no-cache-dir -r requirements.txt

# --- STAGE 2: FINAL (Финальный образ) ---
# Используем меньший, "slim" образ для продакшена (для уменьшения размера)
FROM python:3.11-slim

# Копируем установленные зависимости из "builder"
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Создаем рабочий каталог
WORKDIR /app

# Копируем остальной код
COPY app /app/
COPY main.py /app/main.py

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED 1
ENV PORT 8080

# Команда для запуска приложения Uvicorn/FastAPI
# Убедитесь, что ваш главный скрипт - main.py, а приложение - app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

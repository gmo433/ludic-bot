FROM python:3.1FROM python:3.11-slim

WORKDIR /app

# Ставим системные зависимости (если нужно для сборки)
RUN apt-get update && apt-get install -y build-essential

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY app/ ./app/
COPY k8s/ ./k8s/

EXPOSE 8080

CMD ["python", "app/main.py"]

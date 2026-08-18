# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
COPY scripts/verify_python_lock.py ./verify_python_lock.py
RUN python verify_python_lock.py && pip install --no-cache-dir -r requirements.lock

COPY . .

EXPOSE 8116

CMD ["uvicorn", "notification.main:app", "--host", "0.0.0.0", "--port", "8116"]

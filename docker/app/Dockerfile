FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by Pillow for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for media sync and published content
RUN mkdir -p /data/media-sync/inbox /data/media-sync/cache published

EXPOSE 8111

# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS python-dependencies

WORKDIR /app

# Pillow may require native build tooling on architectures where a wheel is not
# available. Keep this layer before application source so source-only changes
# retain both dependency and browser caches.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
COPY scripts/verify_python_lock.py ./verify_python_lock.py
RUN --mount=type=cache,target=/root/.cache/pip \
    python verify_python_lock.py \
    && pip install --disable-pip-version-check -r requirements.lock

FROM python-dependencies AS runtime-base

# This target deliberately has no browser. It is used by Alembic migration
# jobs, which do not render PDF documents.
COPY . .
RUN mkdir -p /data/media-sync/inbox /data/media-sync/cache published

EXPOSE 8111

FROM python-dependencies AS pdf-runtime

# Both legacy synchronous PDF endpoints and the V2 publication worker launch
# Chromium. Install it in the PDF-capable target only, before source copy so a
# code-only edit never repeats this expensive layer.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps chromium

COPY . .
RUN mkdir -p /data/media-sync/inbox /data/media-sync/cache published

EXPOSE 8111

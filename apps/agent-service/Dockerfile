# ── Stage 1: Builder ───────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install --default-timeout=120 --retries 5 .

# ── Stage 2: Runtime ───────────────────────────────────────────────────────
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/usr/local/bin:$PATH"

COPY --from=builder /install /usr/local

# Install system dependencies for Playwright Chromium & Chromium browser
RUN apt-get update && \
    python -m playwright install --with-deps chromium && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /ms-playwright && \
    chmod -R 777 /ms-playwright

RUN useradd --create-home appuser && \
    mkdir -p /app/logs /app/reports && \
    chown -R appuser:appuser /app

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY start.sh ./start.sh

RUN chmod +x /app/start.sh && chown -R appuser:appuser /app
USER appuser

EXPOSE 8002

CMD ["/app/start.sh"]

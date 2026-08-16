FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY pyproject.toml README.md* ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY start.sh ./start.sh

RUN pip install --no-cache-dir --default-timeout=120 --retries 5 .
RUN playwright install chromium
RUN chmod +x /app/start.sh

EXPOSE 8002

# start.sh runs: alembic upgrade head && uvicorn ...
# The Celery worker container overrides this CMD in docker-compose.yml.
CMD ["/app/start.sh"]

# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 10001 appuser \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_DEFAULT_TIMEOUT=120

# Install deps from PyPI. Optional: populate backend/wheels for offline/flaky networks:
#   pip download -r backend/requirements.txt -d backend/wheels
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/wheels /app/backend/wheels
RUN if ls /app/backend/wheels/*.whl >/dev/null 2>&1; then \
      pip install --no-cache-dir --no-index --find-links=/app/backend/wheels -r /app/backend/requirements.txt; \
    else \
      pip install --no-cache-dir -r /app/backend/requirements.txt; \
    fi

COPY backend/app /app/backend/app
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

COPY --from=frontend-build /frontend/dist /app/frontend/dist

USER appuser
WORKDIR /app/backend
ENV STATIC_DIR=/app/frontend/dist
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]

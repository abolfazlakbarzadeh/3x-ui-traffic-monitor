# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 10001 appuser \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
COPY backend/alembic /app/backend/alembic
COPY backend/alembic.ini /app/backend/alembic.ini
RUN pip install --no-cache-dir /app/backend \
    && pip install --no-cache-dir "uvicorn[standard]>=0.32.0"

COPY --from=frontend-build /frontend/dist /app/frontend/dist
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser
WORKDIR /app/backend
ENV STATIC_DIR=/app/frontend/dist
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]

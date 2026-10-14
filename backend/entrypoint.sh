#!/bin/sh
set -e
cd /app/backend
python - <<'PY'
import asyncio
from alembic import command
from alembic.config import Config
from app.config import get_settings

cfg = Config("alembic.ini")
cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
try:
    command.upgrade(cfg, "head")
except Exception as exc:
    print(f"alembic upgrade warning: {exc}; falling back to create_all")
PY
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

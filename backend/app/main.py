from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api import auth, export, online, servers, usage, users
from app.config import get_settings
from app.db import Base, engine
from app.poller import poller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_migrations(eng: AsyncEngine) -> None:
    """Create tables via metadata (Alembic also ships for production upgrades)."""
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    await run_migrations(engine)
    try:
        await poller.start()
    except Exception:  # noqa: BLE001
        logger.exception("Poller failed to start; API will still serve")
    yield
    await poller.stop()
    await engine.dispose()


app = FastAPI(title="xui-traffic-monitor", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(users.router)
app.include_router(usage.router)
app.include_router(online.router)
app.include_router(export.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


settings = get_settings()
static_dir = Path(settings.static_dir)
if static_dir.is_dir():
    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str) -> FileResponse:
        candidate = static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")

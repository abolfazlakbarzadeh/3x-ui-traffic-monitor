from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api import auth, export, online, servers, settings as settings_api, usage, users
from app.config import get_settings
from app.db import Base, engine
from app.panel_settings import merge_panel_settings
from app.poller import poller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_migrations(eng: AsyncEngine) -> None:
    """Create tables via metadata (Alembic also ships for production upgrades)."""
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_migrations(engine)
    try:
        await poller.start()
    except Exception:  # noqa: BLE001
        logger.exception("Poller failed to start; API will still serve")
    yield
    await poller.stop()
    await engine.dispose()


class DomainGateMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Host does not match web_domain (when set)."""

    def __init__(self, app: ASGIApp, domain: str):
        super().__init__(app)
        self.domain = domain.strip().lower()

    async def dispatch(self, request: Request, call_next):
        if not self.domain:
            return await call_next(request)
        # Always allow health probes
        if request.url.path == "/healthz":
            return await call_next(request)
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host != self.domain:
            return JSONResponse({"detail": "Invalid host"}, status_code=403)
        return await call_next(request)


class BasePathMiddleware:
    """Strip web_base_path prefix; keep /healthz reachable without the prefix."""

    def __init__(self, app: ASGIApp, base_path: str):
        self.app = app
        self.base_path = base_path if base_path != "/" else ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"} or not self.base_path:
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path == "/healthz":
            await self.app(scope, receive, send)
            return

        if path == self.base_path or path.startswith(self.base_path + "/"):
            new_path = path[len(self.base_path) :] or "/"
            scope = dict(scope)
            scope["path"] = new_path
            # Keep raw_path in sync when present
            if "raw_path" in scope:
                scope["raw_path"] = new_path.encode("utf-8")
            await self.app(scope, receive, send)
            return

        await JSONResponse({"detail": "Not found"}, status_code=404)(scope, receive, send)


def create_app() -> FastAPI:
    panel = merge_panel_settings()
    base_path = panel.normalized_base_path()

    app = FastAPI(title="xui-traffic-monitor", lifespan=lifespan)

    app.include_router(auth.router)
    app.include_router(servers.router)
    app.include_router(users.router)
    app.include_router(usage.router)
    app.include_router(online.router)
    app.include_router(export.router)
    app.include_router(settings_api.router)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    settings = get_settings()
    static_dir = Path(settings.static_dir)

    def _inject_base(html: str) -> str:
        snippet = f"<script>window.__XUI_BASE__={base_path!r};</script>"
        if "<head>" in html:
            return html.replace("<head>", f"<head>{snippet}", 1)
        return snippet + html

    if static_dir.is_dir():
        assets = static_dir / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        async def spa(full_path: str) -> Response:
            candidate = static_dir / full_path
            if full_path and candidate.is_file():
                if full_path.endswith(".html"):
                    text = candidate.read_text(encoding="utf-8")
                    return HTMLResponse(_inject_base(text))
                return FileResponse(candidate)
            index = static_dir / "index.html"
            text = index.read_text(encoding="utf-8")
            return HTMLResponse(_inject_base(text))

    # Middleware is LIFO: add domain first so base-path runs first (outer).
    if panel.web_domain:
        app.add_middleware(DomainGateMiddleware, domain=panel.web_domain)
    if base_path != "/":
        app.add_middleware(BasePathMiddleware, base_path=base_path)

    return app


app = create_app()

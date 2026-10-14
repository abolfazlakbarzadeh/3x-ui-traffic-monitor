from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import SessionLocal
from app.delta import SnapshotCounters, compute_delta
from app.models import ClientCurrent, CounterReset, OnlineSession, RawSnapshot, Server
from app.rollup import hour_floor, prune_old_data, upsert_hourly
from app.sources.base import TrafficSource
from app.sources.xui_api import MonitorScopeError
from app.sources.xui_legacy import build_source

logger = logging.getLogger(__name__)


class Poller:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._sources: dict[str, TrafficSource] = {}
        self._server_ids: dict[str, int] = {}
        self._task: asyncio.Task | None = None
        self._online_task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        await self._sync_servers()
        for source in self._sources.values():
            missing = await source.probe_capabilities()
            if missing:
                logger.warning("Capability gaps for %s: %s", source.name, missing)
        self._stop.clear()
        self._task = asyncio.create_task(self._traffic_loop(), name="traffic-poller")
        self._online_task = asyncio.create_task(self._online_loop(), name="online-poller")

    async def stop(self) -> None:
        self._stop.set()
        for task in (self._task, self._online_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        for source in self._sources.values():
            await source.close()
        self._sources.clear()

    async def _sync_servers(self) -> None:
        configs = self.settings.load_servers()
        async with SessionLocal() as session:
            for cfg in configs:
                server = await session.scalar(select(Server).where(Server.name == cfg.name))
                if not server:
                    server = Server(
                        name=cfg.name,
                        base_url=cfg.base_url,
                        web_base_path=cfg.web_base_path,
                        source_mode=cfg.source_mode,
                    )
                    session.add(server)
                    await session.flush()
                else:
                    server.base_url = cfg.base_url
                    server.web_base_path = cfg.web_base_path
                    server.source_mode = cfg.source_mode
                self._server_ids[cfg.name] = server.id
                try:
                    self._sources[cfg.name] = await build_source(cfg)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Failed to build source for %s: %s", cfg.name, exc)
                    server.last_poll_ok = False
                    server.last_error = str(exc)
            await session.commit()

    async def _traffic_loop(self) -> None:
        while not self._stop.is_set():
            await self.poll_traffic_once()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.settings.poll_interval_seconds)
            except TimeoutError:
                continue

    async def _online_loop(self) -> None:
        while not self._stop.is_set():
            await self.poll_online_once()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.settings.online_poll_seconds)
            except TimeoutError:
                continue

    async def poll_traffic_once(self) -> None:
        for name, source in list(self._sources.items()):
            server_id = self._server_ids[name]
            async with SessionLocal() as session:
                try:
                    await self._poll_server_traffic(session, server_id, source)
                    server = await session.get(Server, server_id)
                    if server:
                        server.last_poll_at = datetime.now(UTC)
                        server.last_poll_ok = True
                        server.last_error = None
                    await prune_old_data(
                        session,
                        raw_retention_days=self.settings.raw_retention_days,
                        hourly_retention_days=self.settings.hourly_retention_days,
                        now=datetime.now(UTC),
                    )
                    await session.commit()
                except MonitorScopeError as exc:
                    logger.error("%s", exc)
                    await self._mark_error(session, server_id, str(exc))
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Traffic poll failed for %s", name)
                    await self._mark_error(session, server_id, str(exc))

    async def _mark_error(self, session: AsyncSession, server_id: int, error: str) -> None:
        server = await session.get(Server, server_id)
        if server:
            server.last_poll_at = datetime.now(UTC)
            server.last_poll_ok = False
            server.last_error = error[:2000]
        await session.commit()

    async def _poll_server_traffic(
        self, session: AsyncSession, server_id: int, source: TrafficSource
    ) -> None:
        clients = await source.list_clients()
        now = datetime.now(UTC)
        hour = hour_floor(now)

        for client in clients:
            prev_row = await session.scalar(
                select(RawSnapshot)
                .where(RawSnapshot.server_id == server_id, RawSnapshot.email == client.email)
                .order_by(RawSnapshot.ts.desc())
                .limit(1)
            )
            prev = (
                SnapshotCounters(
                    up=prev_row.up,
                    down=prev_row.down,
                    reset_count=prev_row.reset_count,
                    client_id=prev_row.client_id,
                )
                if prev_row
                else None
            )
            cur = SnapshotCounters(
                up=client.up,
                down=client.down,
                reset_count=client.reset_count,
                client_id=client.client_id,
            )
            result = compute_delta(
                prev,
                cur,
                interval_seconds=self.settings.poll_interval_seconds,
                max_sane_bytes_per_sec=self.settings.max_sane_bytes_per_sec,
            )
            session.add(
                RawSnapshot(
                    server_id=server_id,
                    email=client.email,
                    ts=now,
                    up=client.up,
                    down=client.down,
                    total=client.total,
                    expiry_time=client.expiry_time,
                    enable=client.enable,
                    reset_count=client.reset_count,
                    client_id=client.client_id,
                    last_online=client.last_online,
                )
            )
            if result.is_reset:
                session.add(
                    CounterReset(
                        server_id=server_id,
                        email=client.email,
                        ts=now,
                        reason=result.reset_reason or "reset",
                        prev_up=prev.up if prev else 0,
                        prev_down=prev.down if prev else 0,
                        cur_up=client.up,
                        cur_down=client.down,
                    )
                )
            if not result.is_baseline and (result.up or result.down):
                await upsert_hourly(
                    session,
                    server_id=server_id,
                    email=client.email,
                    hour_start=hour,
                    up=result.up,
                    down=result.down,
                )
            if result.is_anomaly:
                logger.warning(
                    "Anomalous delta for %s/%s: up=%s down=%s",
                    source.name,
                    client.email,
                    result.up,
                    result.down,
                )

            existing = await session.scalar(
                select(ClientCurrent).where(
                    ClientCurrent.server_id == server_id,
                    ClientCurrent.email == client.email,
                )
            )
            if existing:
                existing.client_id = client.client_id
                existing.enable = client.enable
                existing.up = client.up
                existing.down = client.down
                existing.total = client.total
                existing.expiry_time = client.expiry_time
                existing.reset_count = client.reset_count
                existing.last_online = client.last_online
            else:
                session.add(
                    ClientCurrent(
                        server_id=server_id,
                        email=client.email,
                        client_id=client.client_id,
                        enable=client.enable,
                        up=client.up,
                        down=client.down,
                        total=client.total,
                        expiry_time=client.expiry_time,
                        reset_count=client.reset_count,
                        last_online=client.last_online,
                    )
                )

    async def poll_online_once(self) -> None:
        now = datetime.now(UTC)
        for name, source in list(self._sources.items()):
            server_id = self._server_ids[name]
            async with SessionLocal() as session:
                try:
                    onlines = set(await source.get_onlines())
                    open_sessions = (
                        await session.scalars(
                            select(OnlineSession).where(
                                OnlineSession.server_id == server_id,
                                OnlineSession.ended_at.is_(None),
                            )
                        )
                    ).all()
                    open_by_email = {s.email: s for s in open_sessions}
                    for email, session_row in open_by_email.items():
                        if email not in onlines:
                            session_row.ended_at = now
                    for email in onlines:
                        if email not in open_by_email:
                            session.add(
                                OnlineSession(
                                    server_id=server_id,
                                    email=email,
                                    started_at=now,
                                )
                            )
                    await session.commit()
                except Exception:  # noqa: BLE001
                    logger.exception("Online poll failed for %s", name)
                    await session.rollback()


poller = Poller()

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.usage import _floor_hour, _points_from_hourly, _points_from_snapshots
from app.models import RawSnapshot, Server, UsageHourly


@pytest.mark.asyncio
async def test_short_window_includes_overlapping_hour(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        server = Server(name="s", base_url="http://x", web_base_path="/", source_mode="api")
        session.add(server)
        await session.flush()
        hour = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
        session.add(
            UsageHourly(
                server_id=server.id,
                email="u@x",
                hour_start=hour,
                up=1000,
                down=2000,
            )
        )
        await session.commit()

        # Window entirely inside the hour — old filter (hour_start >= start) would miss it
        start = hour + timedelta(minutes=28)
        end = hour + timedelta(minutes=30)
        points = await _points_from_hourly(
            session, server.id, "u@x", start, end, "hour", "UTC"
        )
        assert len(points) == 1
        assert points[0].up == 1000
        assert points[0].down == 2000


@pytest.mark.asyncio
async def test_snapshot_deltas_for_minute_window(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        server = Server(name="s2", base_url="http://x", web_base_path="/", source_mode="api")
        session.add(server)
        await session.flush()
        t0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
        snaps = [
            (t0, 100, 50),
            (t0 + timedelta(minutes=1), 150, 70),
            (t0 + timedelta(minutes=2), 200, 90),
            (t0 + timedelta(minutes=3), 250, 100),
        ]
        for ts, up, down in snaps:
            session.add(
                RawSnapshot(
                    server_id=server.id,
                    email="m@x",
                    ts=ts,
                    up=up,
                    down=down,
                    total=0,
                    expiry_time=0,
                    enable=True,
                    reset_count=0,
                    client_id=1,
                    last_online=0,
                )
            )
        await session.commit()

        start = t0 + timedelta(minutes=1, seconds=30)
        end = t0 + timedelta(minutes=3)
        points = await _points_from_snapshots(session, server.id, "m@x", start, end)
        # Deltas ending at +2m and +3m (150→200 and 200→250)
        assert len(points) == 2
        assert points[0].up == 50 and points[0].down == 20
        assert points[1].up == 50 and points[1].down == 10


def test_floor_hour():
    dt = datetime(2026, 10, 14, 9, 37, 12, tzinfo=UTC)
    assert _floor_hour(dt) == datetime(2026, 10, 14, 9, 0, tzinfo=UTC)

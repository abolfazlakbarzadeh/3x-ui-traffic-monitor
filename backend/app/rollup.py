from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RawSnapshot, UsageHourly


def hour_floor(ts: datetime) -> datetime:
    ts = ts.astimezone() if ts.tzinfo else ts
    return ts.replace(minute=0, second=0, microsecond=0)


def local_day_bounds(ts: datetime, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    local = ts.astimezone(tz)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(day=start.day)  # placeholder; use timedelta below
    from datetime import timedelta

    end = start + timedelta(days=1)
    return start.astimezone(tz), end.astimezone(tz)


async def upsert_hourly(
    session: AsyncSession,
    *,
    server_id: int,
    email: str,
    hour_start: datetime,
    up: int,
    down: int,
) -> None:
    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    if dialect == "postgresql":
        await session.execute(
            text(
                """
                INSERT INTO usage_hourly (server_id, email, hour_start, up, down)
                VALUES (:server_id, :email, :hour_start, :up, :down)
                ON CONFLICT (server_id, email, hour_start)
                DO UPDATE SET up = usage_hourly.up + EXCLUDED.up,
                              down = usage_hourly.down + EXCLUDED.down
                """
            ),
            {
                "server_id": server_id,
                "email": email,
                "hour_start": hour_start,
                "up": up,
                "down": down,
            },
        )
        return

    existing = await session.scalar(
        select(UsageHourly).where(
            UsageHourly.server_id == server_id,
            UsageHourly.email == email,
            UsageHourly.hour_start == hour_start,
        )
    )
    if existing:
        existing.up += up
        existing.down += down
    else:
        session.add(
            UsageHourly(
                server_id=server_id,
                email=email,
                hour_start=hour_start,
                up=up,
                down=down,
            )
        )


async def prune_old_data(
    session: AsyncSession,
    *,
    raw_retention_days: int,
    hourly_retention_days: int,
    now: datetime,
) -> None:
    from datetime import timedelta

    raw_cut = now - timedelta(days=raw_retention_days)
    hourly_cut = now - timedelta(days=hourly_retention_days)
    await session.execute(delete(RawSnapshot).where(RawSnapshot.ts < raw_cut))
    await session.execute(delete(UsageHourly).where(UsageHourly.hour_start < hourly_cut))

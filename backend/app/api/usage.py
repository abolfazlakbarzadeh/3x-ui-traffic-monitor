from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.models import CounterReset, Server, UsageHourly
from app.schemas import TopUser, UsagePoint, UsageSeries
from app.security import AuthUser, get_current_user

router = APIRouter(prefix="/api", tags=["usage"])


@router.get("/users/{server_id}/{email}/usage", response_model=UsageSeries)
async def user_usage(
    server_id: int,
    email: str,
    granularity: str = Query("hour", pattern="^(hour|day|month)$"),
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UsageSeries:
    now = datetime.now(UTC)
    if granularity == "hour":
        start = from_ts or (now - timedelta(hours=48))
        end = to_ts or now
    elif granularity == "day":
        start = from_ts or (now - timedelta(days=90))
        end = to_ts or now
    else:
        start = from_ts or (now - timedelta(days=365))
        end = to_ts or now

    rows = (
        await db.execute(
            select(UsageHourly.hour_start, UsageHourly.up, UsageHourly.down)
            .where(
                UsageHourly.server_id == server_id,
                UsageHourly.email == email,
                UsageHourly.hour_start >= start,
                UsageHourly.hour_start < end,
            )
            .order_by(UsageHourly.hour_start)
        )
    ).all()

    tz = ZoneInfo(settings.tz)
    buckets: dict[datetime, tuple[int, int]] = {}
    for hour_start, up, down in rows:
        local = hour_start.astimezone(tz)
        if granularity == "hour":
            key = hour_start
        elif granularity == "day":
            key = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        else:
            key = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        prev = buckets.get(key, (0, 0))
        buckets[key] = (prev[0] + int(up), prev[1] + int(down))

    points = [
        UsagePoint(bucket_start=k, up=v[0], down=v[1])
        for k, v in sorted(buckets.items(), key=lambda x: x[0])
    ]

    resets = (
        await db.scalars(
            select(CounterReset)
            .where(
                CounterReset.server_id == server_id,
                CounterReset.email == email,
                CounterReset.ts >= start,
                CounterReset.ts < end,
            )
            .order_by(CounterReset.ts)
        )
    ).all()

    return UsageSeries(
        email=email,
        server_id=server_id,
        granularity=granularity,
        points=points,
        resets=[
            {
                "ts": r.ts.isoformat(),
                "reason": r.reason,
                "prev_up": r.prev_up,
                "prev_down": r.prev_down,
                "cur_up": r.cur_up,
                "cur_down": r.cur_down,
            }
            for r in resets
        ],
    )


@router.get("/usage/top", response_model=list[TopUser])
async def top_usage(
    period: str = Query("day", pattern="^(day|month)$"),
    limit: int = Query(10, ge=1, le=100),
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[TopUser]:
    tz = ZoneInfo(settings.tz)
    now = datetime.now(UTC).astimezone(tz)
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_utc = start.astimezone(UTC)

    rows = (
        await db.execute(
            select(
                UsageHourly.server_id,
                Server.name,
                UsageHourly.email,
                func.sum(UsageHourly.up).label("up"),
                func.sum(UsageHourly.down).label("down"),
            )
            .join(Server, Server.id == UsageHourly.server_id)
            .where(UsageHourly.hour_start >= start_utc)
            .group_by(UsageHourly.server_id, Server.name, UsageHourly.email)
            .order_by(func.sum(UsageHourly.up + UsageHourly.down).desc())
            .limit(limit)
        )
    ).all()
    return [
        TopUser(
            server_id=server_id,
            server_name=server_name,
            email=email,
            up=int(up or 0),
            down=int(down or 0),
            total=int((up or 0) + (down or 0)),
        )
        for server_id, server_name, email, up, down in rows
    ]

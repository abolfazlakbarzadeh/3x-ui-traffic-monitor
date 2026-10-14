from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.models import ClientCurrent, OnlineSession, Server, UsageHourly
from app.schemas import UserOut, UsersPage
from app.security import AuthUser, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


def _period_bounds(tz_name: str, now: datetime | None = None) -> tuple[datetime, datetime, datetime, datetime]:
    tz = ZoneInfo(tz_name)
    now = (now or datetime.now(UTC)).astimezone(tz)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    month_start = day_start.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    return (
        day_start.astimezone(UTC),
        day_end.astimezone(UTC),
        month_start.astimezone(UTC),
        month_end.astimezone(UTC),
    )


@router.get("", response_model=UsersPage)
async def list_users(
    server: int | None = None,
    search: str = "",
    sort: str = "email",
    order: str = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UsersPage:
    day_start, day_end, month_start, month_end = _period_bounds(settings.tz)

    today_sq = (
        select(
            UsageHourly.server_id,
            UsageHourly.email,
            (func.coalesce(func.sum(UsageHourly.up + UsageHourly.down), 0)).label("usage_today"),
        )
        .where(UsageHourly.hour_start >= day_start, UsageHourly.hour_start < day_end)
        .group_by(UsageHourly.server_id, UsageHourly.email)
        .subquery()
    )
    month_sq = (
        select(
            UsageHourly.server_id,
            UsageHourly.email,
            (func.coalesce(func.sum(UsageHourly.up + UsageHourly.down), 0)).label("usage_month"),
        )
        .where(UsageHourly.hour_start >= month_start, UsageHourly.hour_start < month_end)
        .group_by(UsageHourly.server_id, UsageHourly.email)
        .subquery()
    )
    online_sq = (
        select(OnlineSession.server_id, OnlineSession.email)
        .where(OnlineSession.ended_at.is_(None))
        .subquery()
    )

    # Sort/filter expressions must use raw byte totals (not display units).
    used_bytes = (ClientCurrent.up + ClientCurrent.down).label("used_bytes")
    usage_today_bytes = func.coalesce(today_sq.c.usage_today, 0).label("usage_today_bytes")
    usage_month_bytes = func.coalesce(month_sq.c.usage_month, 0).label("usage_month_bytes")

    stmt: Select = (
        select(
            ClientCurrent,
            Server.name,
            usage_today_bytes,
            usage_month_bytes,
            online_sq.c.email.is_not(None),
        )
        .join(Server, Server.id == ClientCurrent.server_id)
        .outerjoin(
            today_sq,
            (today_sq.c.server_id == ClientCurrent.server_id)
            & (today_sq.c.email == ClientCurrent.email),
        )
        .outerjoin(
            month_sq,
            (month_sq.c.server_id == ClientCurrent.server_id)
            & (month_sq.c.email == ClientCurrent.email),
        )
        .outerjoin(
            online_sq,
            (online_sq.c.server_id == ClientCurrent.server_id)
            & (online_sq.c.email == ClientCurrent.email),
        )
    )
    if server is not None:
        stmt = stmt.where(ClientCurrent.server_id == server)
    if search:
        stmt = stmt.where(ClientCurrent.email.ilike(f"%{search}%"))

    sort_map = {
        "email": ClientCurrent.email,
        "up": ClientCurrent.up,
        "down": ClientCurrent.down,
        "used": used_bytes,
        "total": ClientCurrent.total,
        "expiry": ClientCurrent.expiry_time,
        "last_online": ClientCurrent.last_online,
        "usage_today": usage_today_bytes,
        "usage_month": usage_month_bytes,
    }
    sort_col = sort_map.get(sort, ClientCurrent.email)
    descending = order.lower() == "desc"
    # nulls_last so missing usage sorts as 0-ish rather than "winning" ASC/DESC oddly
    ordered = sort_col.desc() if descending else sort_col.asc()
    try:
        ordered = ordered.nulls_last()
    except AttributeError:
        pass
    stmt = stmt.order_by(ordered, ClientCurrent.email.asc())

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(await db.scalar(count_stmt) or 0)

    rows = (
        await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    ).all()

    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    items: list[UserOut] = []
    for client, server_name, usage_today, usage_month, is_online in rows:
        used = client.up + client.down
        remaining = None if client.total == 0 else max(0, client.total - used)
        days_left = None
        if client.expiry_time > 0:
            days_left = (client.expiry_time - now_ms) / (1000 * 60 * 60 * 24)
        items.append(
            UserOut(
                server_id=client.server_id,
                server_name=server_name,
                email=client.email,
                enable=client.enable,
                up=client.up,
                down=client.down,
                used=used,
                total=client.total,
                remaining=remaining,
                expiry_time=client.expiry_time,
                days_left=days_left,
                online=bool(is_online),
                last_online=client.last_online,
                usage_today=int(usage_today or 0),
                usage_month=int(usage_month or 0),
            )
        )
    return UsersPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{server_id}/{email}/resets")
async def user_resets(
    server_id: int,
    email: str,
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    from app.models import CounterReset

    rows = (
        await db.scalars(
            select(CounterReset)
            .where(CounterReset.server_id == server_id, CounterReset.email == email)
            .order_by(CounterReset.ts.desc())
            .limit(100)
        )
    ).all()
    return [
        {
            "ts": r.ts.isoformat(),
            "reason": r.reason,
            "prev_up": r.prev_up,
            "prev_down": r.prev_down,
            "cur_up": r.cur_up,
            "cur_down": r.cur_down,
        }
        for r in rows
    ]


@router.get("/{server_id}/{email}/sessions")
async def user_sessions(
    server_id: int,
    email: str,
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (
        await db.scalars(
            select(OnlineSession)
            .where(OnlineSession.server_id == server_id, OnlineSession.email == email)
            .order_by(OnlineSession.started_at.desc())
            .limit(200)
        )
    ).all()
    return [
        {
            "started_at": r.started_at.isoformat(),
            "ended_at": r.ended_at.isoformat() if r.ended_at else None,
        }
        for r in rows
    ]

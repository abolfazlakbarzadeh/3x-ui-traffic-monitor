from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users import list_users
from app.config import Settings, get_settings
from app.db import get_db
from app.security import AuthUser, get_current_user

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/export.csv")
async def export_csv(
    server: int | None = None,
    search: str = "",
    sort: str = "email",
    order: str = "asc",
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    page = await list_users(
        server=server,
        search=search,
        sort=sort,
        order=order,
        page=1,
        page_size=500,
        _=user,
        db=db,
        settings=settings,
    )
    items = list(page.items)
    total = page.total
    current = 1
    while len(items) < total:
        current += 1
        nxt = await list_users(
            server=server,
            search=search,
            sort=sort,
            order=order,
            page=current,
            page_size=500,
            _=user,
            db=db,
            settings=settings,
        )
        if not nxt.items:
            break
        items.extend(nxt.items)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "server_id",
            "server_name",
            "email",
            "enable",
            "up",
            "down",
            "used",
            "total",
            "remaining",
            "expiry_time",
            "days_left",
            "online",
            "last_online",
            "usage_today",
            "usage_month",
        ]
    )
    for u in items:
        writer.writerow(
            [
                u.server_id,
                u.server_name,
                u.email,
                u.enable,
                u.up,
                u.down,
                u.used,
                u.total,
                u.remaining if u.remaining is not None else "",
                u.expiry_time,
                u.days_left if u.days_left is not None else "",
                u.online,
                u.last_online,
                u.usage_today,
                u.usage_month,
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )

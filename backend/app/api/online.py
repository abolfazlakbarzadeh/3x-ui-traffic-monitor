from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models import OnlineSession, Server
from app.schemas import OnlineUser
from app.security import AuthUser, get_current_user

router = APIRouter(prefix="/api/online", tags=["online"])


@router.get("", response_model=list[OnlineUser])
async def list_online(
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OnlineUser]:
    rows = (
        await db.execute(
            select(OnlineSession, Server.name)
            .join(Server, Server.id == OnlineSession.server_id)
            .where(OnlineSession.ended_at.is_(None))
            .order_by(OnlineSession.started_at.desc())
        )
    ).all()
    return [
        OnlineUser(
            server_id=session.server_id,
            server_name=server_name,
            email=session.email,
            started_at=session.started_at,
        )
        for session, server_name in rows
    ]

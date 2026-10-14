from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Server
from app.schemas import ServerOut
from app.security import AuthUser, get_current_user

router = APIRouter(prefix="/api/servers", tags=["servers"])


@router.get("", response_model=list[ServerOut])
async def list_servers(
    _: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Server]:
    result = await db.scalars(select(Server).order_by(Server.name))
    return list(result.all())

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ServerOut(BaseModel):
    id: int
    name: str
    base_url: str
    source_mode: str
    last_poll_at: datetime | None
    last_poll_ok: bool | None
    last_error: str | None

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    server_id: int
    server_name: str
    email: str
    enable: bool
    up: int
    down: int
    used: int
    total: int
    remaining: int | None
    expiry_time: int
    days_left: float | None
    online: bool
    last_online: int
    usage_today: int
    usage_month: int


class UsersPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class UsagePoint(BaseModel):
    bucket_start: datetime
    up: int
    down: int


class UsageSeries(BaseModel):
    email: str
    server_id: int
    granularity: str
    points: list[UsagePoint]
    resets: list[dict[str, Any]] = Field(default_factory=list)


class TopUser(BaseModel):
    server_id: int
    server_name: str
    email: str
    up: int
    down: int
    total: int


class OnlineUser(BaseModel):
    server_id: int
    server_name: str
    email: str
    started_at: datetime

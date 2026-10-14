from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    web_base_path: Mapped[str] = mapped_column(String(256), default="/")
    source_mode: Mapped[str] = mapped_column(String(32), default="api")
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_poll_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RawSnapshot(Base):
    __tablename__ = "raw_snapshots"
    __table_args__ = (
        Index("ix_raw_snapshots_server_email_ts", "server_id", "email", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    up: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    down: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expiry_time: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    enable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    client_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_online: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class UsageHourly(Base):
    __tablename__ = "usage_hourly"
    __table_args__ = (
        UniqueConstraint("server_id", "email", "hour_start", name="uq_usage_hourly"),
        Index("ix_usage_hourly_hour", "hour_start"),
        Index("ix_usage_hourly_server_email", "server_id", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hour_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    up: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    down: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class CounterReset(Base):
    __tablename__ = "counter_resets"
    __table_args__ = (Index("ix_counter_resets_server_email", "server_id", "email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_up: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    prev_down: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cur_up: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cur_down: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class OnlineSession(Base):
    __tablename__ = "online_sessions"
    __table_args__ = (
        Index("ix_online_sessions_open", "server_id", "email", "ended_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClientCurrent(Base):
    __tablename__ = "clients_current"
    __table_args__ = (
        UniqueConstraint("server_id", "email", name="uq_clients_current"),
        Index("ix_clients_current_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    up: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    down: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expiry_time: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    reset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_online: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

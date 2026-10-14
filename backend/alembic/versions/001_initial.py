"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-10-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column("web_base_path", sa.String(length=256), nullable=False, server_default="/"),
        sa.Column("source_mode", sa.String(length=32), nullable=False, server_default="api"),
        sa.Column("last_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_poll_ok", sa.Boolean(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "raw_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("up", sa.BigInteger(), nullable=False),
        sa.Column("down", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False),
        sa.Column("expiry_time", sa.BigInteger(), nullable=False),
        sa.Column("enable", sa.Boolean(), nullable=False),
        sa.Column("reset_count", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("last_online", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_snapshots_server_email_ts", "raw_snapshots", ["server_id", "email", "ts"])
    op.create_table(
        "usage_hourly",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hour_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("up", sa.BigInteger(), nullable=False),
        sa.Column("down", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "email", "hour_start", name="uq_usage_hourly"),
    )
    op.create_index("ix_usage_hourly_hour", "usage_hourly", ["hour_start"])
    op.create_index("ix_usage_hourly_server_email", "usage_hourly", ["server_id", "email"])
    op.create_table(
        "counter_resets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("prev_up", sa.BigInteger(), nullable=False),
        sa.Column("prev_down", sa.BigInteger(), nullable=False),
        sa.Column("cur_up", sa.BigInteger(), nullable=False),
        sa.Column("cur_down", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_counter_resets_server_email", "counter_resets", ["server_id", "email"])
    op.create_table(
        "online_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_online_sessions_open", "online_sessions", ["server_id", "email", "ended_at"])
    op.create_table(
        "clients_current",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("enable", sa.Boolean(), nullable=False),
        sa.Column("up", sa.BigInteger(), nullable=False),
        sa.Column("down", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.BigInteger(), nullable=False),
        sa.Column("expiry_time", sa.BigInteger(), nullable=False),
        sa.Column("reset_count", sa.Integer(), nullable=False),
        sa.Column("last_online", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "email", name="uq_clients_current"),
    )
    op.create_index("ix_clients_current_email", "clients_current", ["email"])


def downgrade() -> None:
    op.drop_table("clients_current")
    op.drop_table("online_sessions")
    op.drop_table("counter_resets")
    op.drop_table("usage_hourly")
    op.drop_table("raw_snapshots")
    op.drop_table("servers")

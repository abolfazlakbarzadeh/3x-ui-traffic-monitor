from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "adminpass")
os.environ.setdefault("XUI_SERVERS", "[]")

from app.db import Base  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session


@pytest.fixture
def admin_password_hash() -> str:
    return hash_password("adminpass")

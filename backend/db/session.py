"""Async engine and session factory for PostgreSQL.

Usage:
    from backend.db.session import async_session, engine
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/market_agent",
)

_is_test = "pytest" in os.environ.get("_", "")

_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}
if _is_test:
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a single session per request."""
    async with async_session() as session:
        yield session

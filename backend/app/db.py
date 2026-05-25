"""Async database engine and session dependency.

NullPool: Supabase's Supavisor already pools connections server-side, so we
don't double-pool here. It also keeps connections from being shared across
asyncio event loops (which matters for the test suite).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import settings

engine = create_async_engine(
    settings.database_url_async,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={"ssl": "require"},  # Supabase requires TLS.
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

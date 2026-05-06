"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from volunteer_call_api.config import settings
from volunteer_call_api.db_url import normalize_async_url

_url, _connect_args = normalize_async_url(settings.database_url)
engine = create_async_engine(_url, echo=False, connect_args=_connect_args)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with async_session_factory() as session:
        yield session

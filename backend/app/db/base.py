from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_session_local: async_sessionmaker[AsyncSession] | None = None


def _get_session_local() -> async_sessionmaker[AsyncSession]:
    global _session_local
    if _session_local is None:
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        _session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return _session_local


async def get_db_session() -> AsyncSession:
    session_local = _get_session_local()
    async with session_local() as session:
        yield session

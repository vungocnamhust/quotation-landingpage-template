from __future__ import annotations

import os
from collections.abc import AsyncIterator
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def _derive_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return database_url


NOTIFICATION_DATABASE_URL = os.getenv(
    "NOTIFICATION_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql+asyncpg://quotation:quotation_password@postgres:5432/notification"),
)

NOTIFICATION_DATABASE_URL_SYNC = os.getenv(
    "NOTIFICATION_DATABASE_URL_SYNC",
    _derive_sync_database_url(NOTIFICATION_DATABASE_URL),
)


class NotificationBase(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_notification_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            NOTIFICATION_DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_notification_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_notification_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


async def get_notification_db() -> AsyncIterator[AsyncSession]:
    async with get_notification_session_factory()() as session:
        yield session

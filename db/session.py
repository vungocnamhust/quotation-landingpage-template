from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

engine = None
AsyncSessionLocal = None


def install_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """Enforces SQLite foreign keys on all connections.

    SQLite has FK support compiled in but disabled per-connection by default.
    Without this, declared model FKs are inert — invalid references silently persist
    here while the same call raises IntegrityError on Postgres (Track 1 audit H2/R-H1).
    """
    if engine.sync_engine.dialect.name == "sqlite":
        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global engine
    global AsyncSessionLocal

    if AsyncSessionLocal is None:
        engine_kwargs: dict[str, object] = {"echo": settings.db_echo, "pool_pre_ping": True}
        if not settings.database_url.startswith("sqlite"):
            # QueuePool-only options: SQLite (NullPool/StaticPool by default) rejects
            # them outright, and only Postgres deployments need pool tuning here.
            engine_kwargs.update(
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
            )
        engine = create_async_engine(settings.database_url, **engine_kwargs)
        install_sqlite_foreign_keys(engine)
        AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return AsyncSessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session

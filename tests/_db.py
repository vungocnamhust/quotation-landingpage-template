"""Shared test database engine factory.

Enforces PRAGMA foreign_keys=ON on SQLite engines across the entire test suite
(Track 1 audit R-H1) so declared foreign keys are never inert during test execution.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from db.base import Base
from db.session import install_sqlite_foreign_keys


@event.listens_for(Base.metadata, "before_drop")
def _disable_sqlite_fk_before_drop(target: Any, connection: Any, **kw: Any) -> None:
    if connection.dialect.name == "sqlite":
        connection.execute(text("PRAGMA foreign_keys=OFF"))


@event.listens_for(Base.metadata, "after_drop")
def _enable_sqlite_fk_after_drop(target: Any, connection: Any, **kw: Any) -> None:
    if connection.dialect.name == "sqlite":
        connection.execute(text("PRAGMA foreign_keys=ON"))


def make_test_engine(*args: Any, **kwargs: Any) -> AsyncEngine:
    engine = create_async_engine(*args, **kwargs)
    install_sqlite_foreign_keys(engine)
    return engine

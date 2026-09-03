import asyncio
import dataclasses
import os
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import db.session as db_session
from db.base import Base
from db.models.product import Product


class SqliteForeignKeyEnforcementTests(unittest.TestCase):
    """Track 1 audit H2 (systemic half): get_session_factory() must enable
    PRAGMA foreign_keys=ON for SQLite, or declared model FKs are inert and a
    dangling reference silently persists in every test/dev run while the same
    call would 500 on Postgres."""

    def setUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.database_file.close()
        db_session.engine = None
        db_session.AsyncSessionLocal = None
        sqlite_settings = dataclasses.replace(
            db_session.settings, database_url=f"sqlite+aiosqlite:///{self.database_file.name}"
        )
        self._settings_patch = patch.object(db_session, "settings", sqlite_settings)
        self._settings_patch.start()

    def tearDown(self):
        asyncio.run(self._dispose())
        self._settings_patch.stop()
        db_session.engine = None
        db_session.AsyncSessionLocal = None
        os.unlink(self.database_file.name)

    async def _dispose(self):
        if db_session.engine is not None:
            await db_session.engine.dispose()

    def test_pragma_foreign_keys_is_on_for_every_new_connection(self):
        async def scenario():
            session_factory = db_session.get_session_factory()
            async with session_factory() as session:
                result = await session.execute(text("PRAGMA foreign_keys"))
                self.assertEqual(result.scalar(), 1)

        asyncio.run(scenario())

    def test_dangling_fk_insert_raises_integrity_error(self):
        async def scenario():
            session_factory = db_session.get_session_factory()
            async with db_session.engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

            async with session_factory() as session:
                session.add(
                    Product(
                        id="prd_dangling",
                        destination_id="dst_does_not_exist",
                        category="ticket",
                        title="Dangling FK Product",
                        title_normalized="dangling fk product",
                        unit="person",
                        time_basis="trip",
                    )
                )
                with self.assertRaises(IntegrityError):
                    await session.flush()

    def test_make_test_engine_enforces_sqlite_foreign_keys(self):
        """Track 1 audit R-H1: make_test_engine() must enforce PRAGMA foreign_keys=ON."""
        from tests._db import make_test_engine

        async def scenario():
            # In-memory engine
            mem_engine = make_test_engine("sqlite+aiosqlite:///:memory:")
            async with mem_engine.connect() as conn:
                res = await conn.execute(text("PRAGMA foreign_keys"))
                self.assertEqual(res.scalar(), 1)
            await mem_engine.dispose()

            # File-based engine
            file_engine = make_test_engine(f"sqlite+aiosqlite:///{self.database_file.name}")
            async with file_engine.connect() as conn:
                res = await conn.execute(text("PRAGMA foreign_keys"))
                self.assertEqual(res.scalar(), 1)
            await file_engine.dispose()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()


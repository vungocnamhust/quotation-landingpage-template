import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import main
from db.base import Base


class DestinationCatalogCrudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.database_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._create_schema())
        cls.session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.auth_patch = patch.dict(os.environ, {"DMC_GATEWAY_ENABLED": "false", "QUOTE_AUTH_REQUIRED": "false", "ENVIRONMENT": "local"})
        cls.auth_patch.start()
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.auth_patch.stop()
        cls.session_patch.stop()
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.database_file.name)

    @classmethod
    async def _create_schema(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    def test_create_read_update_deactivate_and_reject_invalid_coordinates(self):
        payload = {
            "canonicalName": "Test Map City",
            "slug": "test-map-city",
            "aliases": ["Test City"],
            "countrySlug": "vietnam",
            "regionSlug": "north",
            "provinceSlug": "test",
            "latitude": 21.0285,
            "longitude": 105.8542,
        }
        created = self.client.post("/api/v2/destinations", json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        destination = created.json()
        self.assertTrue(destination["id"].startswith("dst_"))
        self.assertEqual(destination["latitude"], 21.0285)

        read = self.client.get(f"/api/v2/destinations/{destination['id']}")
        self.assertEqual(read.status_code, 200, read.text)
        self.assertIn("test city", read.json()["aliases"])

        updated = self.client.put(f"/api/v2/destinations/{destination['id']}", json={**payload, "canonicalName": "Updated Map City", "latitude": 21.1})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["slug"], "test-map-city")
        self.assertEqual(updated.json()["latitude"], 21.1)

        deactivated = self.client.patch(f"/api/v2/destinations/{destination['id']}/status", json={"isActive": False})
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertFalse(deactivated.json()["isActive"])

        invalid = self.client.post("/api/v2/destinations", json={**payload, "slug": "invalid-map-city", "latitude": 91})
        self.assertEqual(invalid.status_code, 422)


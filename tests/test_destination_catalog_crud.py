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

    def test_search_and_filter_destinations(self):
        # 1. Create active destination in Thailand
        th_payload = {
            "canonicalName": "Bangkok Test",
            "slug": "bangkok-test",
            "aliases": ["Krung Thep"],
            "countrySlug": "thailand",
            "regionSlug": "central",
            "provinceSlug": "bangkok",
            "latitude": 13.7563,
            "longitude": 100.5018,
        }
        th_created = self.client.post("/api/v2/destinations", json=th_payload)
        self.assertEqual(th_created.status_code, 201)
        th_id = th_created.json()["id"]

        # 2. Search all with active=true
        res_active = self.client.get("/api/v2/destinations?active=true")
        self.assertEqual(res_active.status_code, 200)
        items_active = res_active.json()["items"]
        self.assertTrue(any(item["id"] == th_id for item in items_active))

        # 3. Filter by countrySlug=thailand
        res_country = self.client.get("/api/v2/destinations?countrySlug=thailand")
        self.assertEqual(res_country.status_code, 200)
        items_country = res_country.json()["items"]
        self.assertTrue(all(item["countrySlug"] == "thailand" for item in items_country))
        self.assertTrue(any(item["id"] == th_id for item in items_country))

        # 4. Deactivate and check active=false and active=all
        self.client.patch(f"/api/v2/destinations/{th_id}/status", json={"isActive": False})
        res_inactive = self.client.get("/api/v2/destinations?active=false")
        self.assertEqual(res_inactive.status_code, 200)
        items_inactive = res_inactive.json()["items"]
        self.assertTrue(any(item["id"] == th_id for item in items_inactive))

        res_all = self.client.get("/api/v2/destinations?active=all")
        self.assertEqual(res_all.status_code, 200)
        items_all = res_all.json()["items"]
        self.assertTrue(any(item["id"] == th_id for item in items_all))

    def test_reactivating_a_merged_destination_via_status_endpoint_is_rejected(self):
        """Track 1 audit C1, HTTP layer."""
        source_payload = {
            "canonicalName": "Merge Source City",
            "slug": "merge-source-city",
            "aliases": [],
            "latitude": 10.0,
            "longitude": 106.0,
        }
        target_payload = {
            "canonicalName": "Merge Target City",
            "slug": "merge-target-city",
            "aliases": [],
            "latitude": 10.1,
            "longitude": 106.1,
        }
        source_id = self.client.post("/api/v2/destinations", json=source_payload).json()["id"]
        target_id = self.client.post("/api/v2/destinations", json=target_payload).json()["id"]

        merged = self.client.post(f"/api/v2/destinations/{source_id}/merge", json={"targetId": target_id})
        self.assertEqual(merged.status_code, 200, merged.text)

        reactivated = self.client.patch(f"/api/v2/destinations/{source_id}/status", json={"isActive": True})
        self.assertEqual(reactivated.status_code, 422, reactivated.text)



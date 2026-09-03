import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import db.session as db_session
import main
from db.base import Base


class SupplierApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.database_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._create_schema())
        # Suppliers use DbSessionDep -> db.session.get_db, which resolves its
        # engine from db.session.get_session_factory() — patch that (not
        # main._get_db_session_factory, which only backs the ActorRef-style
        # `import main; main._get_db_session_factory()` helper other routers use).
        cls.session_patch = patch.object(db_session, "get_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.auth_patch = patch.dict(
            os.environ, {"DMC_GATEWAY_ENABLED": "false", "QUOTE_AUTH_REQUIRED": "false", "ENVIRONMENT": "local"}
        )
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

    def setUp(self):
        asyncio.run(self._reset_tables())

    async def _reset_tables(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    def _base_payload(self, **overrides):
        payload = {
            "name": "Fansipan Legend DMC",
            "supplier_type": "dmc",
            "default_currency": "USD",
            "preferred_status": "preferred",
            "quality_tier": "luxury",
            "contact_json": {"person": "An Nguyen", "email": "an@fansipanlegend.example"},
        }
        payload.update(overrides)
        return payload

    def test_create_read_update_and_status_lifecycle(self):
        created = self.client.post("/api/v2/suppliers", json=self._base_payload())
        self.assertEqual(created.status_code, 201, created.text)
        supplier = created.json()
        self.assertTrue(supplier["id"].startswith("sup_"))
        self.assertEqual(supplier["default_currency"], "USD")
        self.assertTrue(supplier["is_active"])

        read = self.client.get(f"/api/v2/suppliers/{supplier['id']}")
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()["name"], "Fansipan Legend DMC")

        updated = self.client.put(
            f"/api/v2/suppliers/{supplier['id']}",
            json={"quality_tier": "ultra_luxury", "credit_terms_days": 30},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["quality_tier"], "ultra_luxury")
        self.assertEqual(updated.json()["credit_terms_days"], 30)

        deactivated = self.client.patch(f"/api/v2/suppliers/{supplier['id']}/status", json={"isActive": False})
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertFalse(deactivated.json()["is_active"])

    def test_duplicate_name_conflicts_with_409(self):
        first = self.client.post("/api/v2/suppliers", json=self._base_payload())
        self.assertEqual(first.status_code, 201, first.text)

        duplicate = self.client.post("/api/v2/suppliers", json=self._base_payload(name="  fansipan legend dmc "))
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    def test_get_unknown_supplier_returns_404(self):
        response = self.client.get("/api/v2/suppliers/sup_does_not_exist")
        self.assertEqual(response.status_code, 404)

    def test_filter_by_active_and_supplier_type_and_search(self):
        dmc = self.client.post("/api/v2/suppliers", json=self._base_payload(name="Hanoi DMC Co")).json()
        hotel = self.client.post(
            "/api/v2/suppliers",
            json=self._base_payload(name="La Siesta Hotel", supplier_type="direct"),
        ).json()
        self.client.patch(f"/api/v2/suppliers/{hotel['id']}/status", json={"isActive": False})

        by_type = self.client.get("/api/v2/suppliers?active=all&supplier_type=dmc")
        self.assertEqual(by_type.status_code, 200)
        type_ids = {item["id"] for item in by_type.json()["items"]}
        self.assertIn(dmc["id"], type_ids)
        self.assertNotIn(hotel["id"], type_ids)

        inactive = self.client.get("/api/v2/suppliers?active=false")
        self.assertEqual(inactive.status_code, 200)
        inactive_ids = {item["id"] for item in inactive.json()["items"]}
        self.assertIn(hotel["id"], inactive_ids)

        searched = self.client.get("/api/v2/suppliers?active=all&search=siesta")
        self.assertEqual(searched.status_code, 200)
        searched_ids = {item["id"] for item in searched.json()["items"]}
        self.assertIn(hotel["id"], searched_ids)
        self.assertNotIn(dmc["id"], searched_ids)

    def test_status_update_requires_is_active_field(self):
        created = self.client.post("/api/v2/suppliers", json=self._base_payload())
        supplier_id = created.json()["id"]

        response = self.client.patch(f"/api/v2/suppliers/{supplier_id}/status", json={})
        self.assertEqual(response.status_code, 422)

    def test_invalid_supplier_type_returns_422(self):
        response = self.client.post("/api/v2/suppliers", json=self._base_payload(supplier_type="not-a-real-type"))
        self.assertEqual(response.status_code, 422)

    def test_search_by_contact_person_finds_supplier(self):
        """Track 1 audit M1."""
        target = self.client.post(
            "/api/v2/suppliers",
            json=self._base_payload(name="Sapa Trekking Co", contact_json={"person": "Mai Anh Tran"}),
        ).json()
        self.client.post("/api/v2/suppliers", json=self._base_payload(name="Unrelated Co"))

        response = self.client.get("/api/v2/suppliers?active=all&search=Mai Anh")
        self.assertEqual(response.status_code, 200, response.text)
        ids = {item["id"] for item in response.json()["items"]}
        self.assertIn(target["id"], ids)

    def test_pagination_total_reflects_full_filtered_count_not_page_size(self):
        """Track 1 audit H4."""
        for i in range(5):
            self.client.post("/api/v2/suppliers", json=self._base_payload(name=f"Pagination Supplier {i}"))

        response = self.client.get("/api/v2/suppliers?limit=2")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(len(body["items"]), 2)
        self.assertEqual(body["total"], 5)

    def test_unsupported_currency_returns_422_not_409(self):
        """Track 1 audit M2."""
        response = self.client.post("/api/v2/suppliers", json=self._base_payload(default_currency="XYZ"))
        self.assertEqual(response.status_code, 422, response.text)

    def test_unknown_destination_id_returns_422_not_500(self):
        """Track 1 audit H2."""
        response = self.client.post(
            "/api/v2/suppliers", json=self._base_payload(destination_id="dst_does_not_exist")
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_blank_name_returns_422(self):
        """Track 1 audit M3."""
        response = self.client.post("/api/v2/suppliers", json=self._base_payload(name="   "))
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()

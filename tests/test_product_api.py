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
from db.models.accommodation import AccommodationProfile
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier


class ProductApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.database_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._create_schema())
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
        async with self.session_factory() as session:
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            session.add(DestinationCatalog(id="dst_hue", canonical_name="Hue", slug="hue"))
            session.add(
                AccommodationProfile(
                    id="acc_la_siesta",
                    destination_id="dst_hanoi",
                    storage_slug="la-siesta",
                    asset_prefix="hanoi/la-siesta",
                    name="La Siesta Hotel",
                )
            )
            session.add(
                Supplier(
                    id="sup_dummy",
                    name="Dummy Supplier",
                    name_normalized="dummy supplier",
                    supplier_type="dmc",
                    default_currency="USD",
                )
            )
            await session.commit()

    def _base_payload(self, **overrides):
        payload = {
            "destination_id": "dst_hanoi",
            "category": "ticket",
            "title": "Old Quarter Walking Tour",
        }
        payload.update(overrides)
        return payload

    def test_create_read_update_and_status_lifecycle(self):
        created = self.client.post("/api/v2/products", json=self._base_payload())
        self.assertEqual(created.status_code, 201, created.text)
        product = created.json()
        self.assertTrue(product["id"].startswith("prd_"))
        self.assertEqual(product["unit"], "person")
        self.assertEqual(product["time_basis"], "trip")
        self.assertTrue(product["is_active"])
        self.assertIsNone(product["supplier_id"])

        read = self.client.get(f"/api/v2/products/{product['id']}")
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()["title"], "Old Quarter Walking Tour")

        updated = self.client.put(
            f"/api/v2/products/{product['id']}",
            json={"title": "Old Quarter Heritage Walking Tour"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "Old Quarter Heritage Walking Tour")

        deactivated = self.client.patch(f"/api/v2/products/{product['id']}/status", json={"isActive": False})
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertFalse(deactivated.json()["is_active"])

    def test_duplicate_dedupe_key_conflicts_with_409(self):
        first = self.client.post("/api/v2/products", json=self._base_payload())
        self.assertEqual(first.status_code, 201, first.text)

        duplicate = self.client.post("/api/v2/products", json=self._base_payload(title="  old quarter walking tour "))
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    def test_get_unknown_product_returns_404(self):
        response = self.client.get("/api/v2/products/prd_does_not_exist")
        self.assertEqual(response.status_code, 404)

    def test_filter_by_category_destination_supplier_and_search(self):
        ticket = self.client.post("/api/v2/products", json=self._base_payload()).json()
        meal = self.client.post(
            "/api/v2/products",
            json=self._base_payload(category="meal", title="Welcome Dinner", supplier_id="sup_dummy"),
        ).json()
        self.client.patch(f"/api/v2/products/{meal['id']}/status", json={"isActive": False})

        by_category = self.client.get("/api/v2/products?active=all&category=ticket")
        self.assertEqual(by_category.status_code, 200)
        category_ids = {item["id"] for item in by_category.json()["items"]}
        self.assertIn(ticket["id"], category_ids)
        self.assertNotIn(meal["id"], category_ids)

        by_supplier = self.client.get("/api/v2/products?active=all&supplier_id=sup_dummy")
        self.assertEqual(by_supplier.status_code, 200)
        supplier_ids = {item["id"] for item in by_supplier.json()["items"]}
        self.assertIn(meal["id"], supplier_ids)
        self.assertNotIn(ticket["id"], supplier_ids)

        inactive = self.client.get("/api/v2/products?active=false")
        self.assertEqual(inactive.status_code, 200)
        inactive_ids = {item["id"] for item in inactive.json()["items"]}
        self.assertIn(meal["id"], inactive_ids)

        searched = self.client.get("/api/v2/products?active=all&search=dinner")
        self.assertEqual(searched.status_code, 200)
        searched_ids = {item["id"] for item in searched.json()["items"]}
        self.assertIn(meal["id"], searched_ids)
        self.assertNotIn(ticket["id"], searched_ids)

    def test_filter_by_property_id(self):
        room = self.client.post(
            "/api/v2/products",
            json=self._base_payload(category="accommodation", title="La Siesta Deluxe", property_id="acc_la_siesta"),
        )
        self.assertEqual(room.status_code, 201, room.text)
        room_id = room.json()["id"]

        by_property = self.client.get("/api/v2/products?active=all&property_id=acc_la_siesta")
        self.assertEqual(by_property.status_code, 200)
        self.assertIn(room_id, {item["id"] for item in by_property.json()["items"]})

    def test_status_update_requires_is_active_field(self):
        created = self.client.post("/api/v2/products", json=self._base_payload())
        product_id = created.json()["id"]

        response = self.client.patch(f"/api/v2/products/{product_id}/status", json={})
        self.assertEqual(response.status_code, 422)

    def test_invalid_category_returns_422(self):
        response = self.client.post("/api/v2/products", json=self._base_payload(category="not-a-real-category"))
        self.assertEqual(response.status_code, 422)

    def test_property_id_with_wrong_category_returns_422(self):
        response = self.client.post(
            "/api/v2/products",
            json=self._base_payload(category="ticket", property_id="acc_la_siesta"),
        )
        self.assertEqual(response.status_code, 422)

    def test_invalid_subcategory_for_category_returns_422(self):
        response = self.client.post(
            "/api/v2/products",
            json=self._base_payload(category="accommodation", subcategory="car_4_seat", title="Bad Subcategory"),
        )
        self.assertEqual(response.status_code, 422)

    def test_update_supplier_product_name_is_rejected_with_422(self):
        created = self.client.post(
            "/api/v2/products",
            json=self._base_payload(supplier_product_name="Original Source Name"),
        )
        product_id = created.json()["id"]

        response = self.client.put(f"/api/v2/products/{product_id}", json={"supplier_product_name": "Changed"})
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()

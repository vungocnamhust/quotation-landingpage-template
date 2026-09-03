import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

import db.session as db_session
import main
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier


class RateApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.database_file.close()
        cls.engine = make_test_engine(f"sqlite+aiosqlite:///{cls.database_file.name}")
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
        self.product_id = self._create_product()

    async def _reset_tables(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with self.session_factory() as session:
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            session.add(
                Supplier(
                    id="sup_la_siesta",
                    name="La Siesta Hotel Group",
                    name_normalized="la siesta hotel group",
                    supplier_type="direct",
                    default_currency="USD",
                )
            )
            await session.commit()

    def _create_product(self) -> str:
        response = self.client.post(
            "/api/v2/products",
            json={
                "destination_id": "dst_hanoi",
                "category": "accommodation",
                "title": "La Siesta Old Quarter — Deluxe Room",
                "supplier_id": "sup_la_siesta",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    def _rate_payload(self, **overrides):
        payload = {
            "product_id": self.product_id,
            "rate_basis": "net",
            "valid_from": "2026-01-01",
            "valid_to": "2026-03-31",
            "season_name": "Winter 2026",
            "lines": [
                {"price_for": "adult", "occupancy_basis": "na", "unit": "person", "amount_minor": 1_000_000},
            ],
        }
        payload.update(overrides)
        return payload

    def test_create_activate_supersede_lifecycle(self):
        created = self.client.post(f"/api/v2/products/{self.product_id}/rates", json=self._rate_payload())
        self.assertEqual(created.status_code, 201, created.text)
        rate = created.json()
        self.assertEqual(rate["currency"], "USD")
        self.assertEqual(rate["lifecycle_status"], "draft")

        activated = self.client.post(f"/api/v2/rates/{rate['id']}/activate")
        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertEqual(activated.json()["lifecycle_status"], "active")

        superseded = self.client.post(
            f"/api/v2/rates/{rate['id']}/supersede",
            json=self._rate_payload(valid_from="2026-04-01", valid_to="2026-06-30"),
        )
        self.assertEqual(superseded.status_code, 201, superseded.text)
        new_rate = superseded.json()
        self.assertEqual(new_rate["version"], 2)
        self.assertEqual(new_rate["supersedes_rate_id"], rate["id"])

        old_reloaded = self.client.get(f"/api/v2/rates/{rate['id']}")
        self.assertEqual(old_reloaded.status_code, 200)
        self.assertEqual(old_reloaded.json()["lifecycle_status"], "superseded")

    def test_put_on_active_rate_returns_409(self):
        created = self.client.post(f"/api/v2/products/{self.product_id}/rates", json=self._rate_payload()).json()
        self.client.post(f"/api/v2/rates/{created['id']}/activate")

        response = self.client.put(f"/api/v2/rates/{created['id']}", json=self._rate_payload(season_name="Edited"))
        self.assertEqual(response.status_code, 409, response.text)

    def test_update_draft_succeeds(self):
        created = self.client.post(f"/api/v2/products/{self.product_id}/rates", json=self._rate_payload()).json()

        response = self.client.put(
            f"/api/v2/rates/{created['id']}",
            json=self._rate_payload(
                season_name="Edited",
                lines=[
                    {"price_for": "adult", "occupancy_basis": "na", "unit": "person", "amount_minor": 111},
                    {"price_for": "child", "occupancy_basis": "na", "unit": "person", "amount_minor": 222},
                ],
            ),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["season_name"], "Edited")
        self.assertEqual([(line["price_for"], line["amount_minor"]) for line in response.json()["lines"]], [("adult", 111), ("child", 222)])

    def test_duplicate_price_line_combo_and_unknown_source_return_422(self):
        duplicate = self.client.post(
            f"/api/v2/products/{self.product_id}/rates",
            json=self._rate_payload(
                lines=[
                    {"price_for": "adult", "occupancy_basis": "na", "unit": "person", "amount_minor": 1},
                    {"price_for": "adult", "occupancy_basis": "na", "unit": "person", "amount_minor": 2},
                ]
            ),
        )
        self.assertEqual(duplicate.status_code, 422, duplicate.text)
        self.assertEqual(duplicate.json()["error"]["code"], "VALIDATION_FAILED")

        missing_source = self.client.post(
            f"/api/v2/products/{self.product_id}/rates",
            json=self._rate_payload(source={"supplier_id": "sup_missing"}),
        )
        self.assertEqual(missing_source.status_code, 422, missing_source.text)
        self.assertEqual(missing_source.json()["error"]["code"], "VALIDATION_FAILED")

    def test_activate_without_lines_returns_422(self):
        created = self.client.post(f"/api/v2/products/{self.product_id}/rates", json=self._rate_payload(lines=[])).json()

        response = self.client.post(f"/api/v2/rates/{created['id']}/activate")
        self.assertEqual(response.status_code, 422, response.text)

    def test_get_unknown_rate_returns_404(self):
        response = self.client.get("/api/v2/rates/rat_does_not_exist")
        self.assertEqual(response.status_code, 404)

    def test_create_rate_for_unknown_product_returns_404(self):
        response = self.client.post("/api/v2/products/prd_does_not_exist/rates", json=self._rate_payload())
        self.assertEqual(response.status_code, 404)

    def test_list_by_product_defaults_to_active_and_filters_on_date(self):
        created = self.client.post(f"/api/v2/products/{self.product_id}/rates", json=self._rate_payload()).json()
        self.client.post(f"/api/v2/rates/{created['id']}/activate")

        default_list = self.client.get(f"/api/v2/products/{self.product_id}/rates")
        self.assertEqual(default_list.status_code, 200)
        self.assertEqual(default_list.json()["total"], 1)
        self.assertEqual(default_list.json()["items"][0]["lines"][0]["amount_minor"], 1_000_000)

        in_range = self.client.get(f"/api/v2/products/{self.product_id}/rates?on_date=2026-02-01")
        self.assertEqual(in_range.json()["total"], 1)

        out_of_range = self.client.get(f"/api/v2/products/{self.product_id}/rates?on_date=2026-12-01")
        self.assertEqual(out_of_range.json()["total"], 0)

    def test_list_total_counts_beyond_limit_and_excludes_blackout(self):
        for month in (1, 4, 7):
            created = self.client.post(
                f"/api/v2/products/{self.product_id}/rates",
                json=self._rate_payload(
                    valid_from=f"2026-{month:02d}-01",
                    valid_to=f"2026-{month + 2:02d}-28",
                    blackout_json=[{"from": f"2026-{month:02d}-15", "to": f"2026-{month:02d}-15"}],
                ),
            ).json()
            self.assertEqual(self.client.post(f"/api/v2/rates/{created['id']}/activate").status_code, 200)

        paged = self.client.get(f"/api/v2/products/{self.product_id}/rates?limit=1")
        self.assertEqual(paged.status_code, 200, paged.text)
        self.assertEqual(len(paged.json()["items"]), 1)
        self.assertEqual(paged.json()["total"], 3)

        blackout = self.client.get(f"/api/v2/products/{self.product_id}/rates?on_date=2026-04-15")
        self.assertEqual(blackout.status_code, 200, blackout.text)
        self.assertEqual(blackout.json()["total"], 0)

    def test_hard_delete_draft(self):
        created = self.client.post(f"/api/v2/products/{self.product_id}/rates", json=self._rate_payload()).json()

        response = self.client.delete(f"/api/v2/rates/{created['id']}")
        self.assertEqual(response.status_code, 204, response.text)

        follow_up = self.client.get(f"/api/v2/rates/{created['id']}")
        self.assertEqual(follow_up.status_code, 404)

    def test_hard_delete_active_rate_returns_409(self):
        created = self.client.post(f"/api/v2/products/{self.product_id}/rates", json=self._rate_payload()).json()
        self.client.post(f"/api/v2/rates/{created['id']}/activate")

        response = self.client.delete(f"/api/v2/rates/{created['id']}")
        self.assertEqual(response.status_code, 409, response.text)


if __name__ == "__main__":
    unittest.main()

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
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from repositories.quote_request_repository import QuoteRequestRepository
from repositories.quotation_repository import QuotationRepository


class ApApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.database_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.database_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._create_schema())
        cls.session_patch = patch.object(db_session, "get_session_factory", return_value=cls.session_factory)
        cls.session_patch.start()
        cls.main_session_patch = patch.object(main, "_get_db_session_factory", return_value=cls.session_factory)
        cls.main_session_patch.start()
        cls.auth_patch = patch.dict(
            os.environ, {"DMC_GATEWAY_ENABLED": "false", "QUOTE_AUTH_REQUIRED": "false", "ENVIRONMENT": "local"}
        )
        cls.auth_patch.start()
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.auth_patch.stop()
        cls.main_session_patch.stop()
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
            session.add(
                Supplier(
                    id="sup_la_siesta",
                    name="La Siesta Hotel Group",
                    name_normalized="la siesta hotel group",
                    supplier_type="direct",
                    default_currency="USD",
                    credit_terms_days=30,
                )
            )
            await session.commit()
            await QuoteRequestRepository(session).create_request(
                role="customer", customer_name="Jane Doe", email="jane@example.com", request_id="req_apapi1"
            )
            await session.commit()
            await QuotationRepository(session).create_quotation(
                quotation_id="qtn_apapi1", brand_id="brand_capella", template_name="quote-generator", baseline_lang="en"
            )
            await session.commit()

    def _create_invoice(self, **overrides):
        payload = {
            "supplierId": "sup_la_siesta",
            "invoiceDate": "2026-06-20",
            "currency": "USD",
            "grossTotalMinor": 2_000_000,
        }
        payload.update(overrides)
        response = self.client.post("/api/v2/ap/invoices", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_get_and_list_invoice(self):
        invoice = self._create_invoice()
        self.assertEqual(invoice["status"], "draft")

        response = self.client.get(f"/api/v2/ap/invoices/{invoice['id']}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["id"], invoice["id"])

        response = self.client.get("/api/v2/ap/invoices", params={"supplierId": "sup_la_siesta"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["items"]), 1)

    def test_get_missing_invoice_returns_404(self):
        response = self.client.get("/api/v2/ap/invoices/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_record_then_upsert_lines_then_approve_blocked_when_unmatched(self):
        invoice = self._create_invoice()
        response = self.client.put(
            f"/api/v2/ap/invoices/{invoice['id']}",
            json={"baseInvoiceRevision": invoice["invoice_revision"], "action": "record"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        invoice = response.json()
        self.assertEqual(invoice["status"], "received")

        response = self.client.put(
            f"/api/v2/ap/invoices/{invoice['id']}/lines",
            json={
                "baseInvoiceRevision": invoice["invoice_revision"],
                "lines": [{"lineType": "service", "description": "Room x2 nights", "amountMinor": 2_000_000}],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        invoice = response.json()
        self.assertEqual(len(invoice["lines"]), 1)

        response = self.client.post(
            f"/api/v2/ap/invoices/{invoice['id']}/approve", json={"baseInvoiceRevision": invoice["invoice_revision"]}
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_stale_revision_returns_409_envelope(self):
        invoice = self._create_invoice()
        response = self.client.put(
            f"/api/v2/ap/invoices/{invoice['id']}",
            json={"baseInvoiceRevision": invoice["invoice_revision"] + 1, "action": "record"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        body = response.json()
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], "REVISION_CONFLICT")

    def test_match_line_action_route_rejects_unknown_action(self):
        invoice = self._create_invoice()
        self.client.put(
            f"/api/v2/ap/invoices/{invoice['id']}",
            json={"baseInvoiceRevision": invoice["invoice_revision"], "action": "record"},
        )
        response = self.client.post(
            f"/api/v2/ap/invoices/{invoice['id']}/lines/1/bogus-action", json={"baseInvoiceRevision": 1}
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

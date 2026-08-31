import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import db.session as db_session
import main
import services.ingestion.extraction_service as extraction_service
import services.ingestion.resolution_service as resolution_service
from db.base import Base
from db.models.destination import DestinationAlias, DestinationCatalog
from schemas.catalog_ingest import (
    CatalogIngestPayload,
    ProductCandidate,
    ResolutionEntry,
    ResolutionPlan,
    SupplierCandidate,
)
from services.ai_platform.guardrails import AllowlistRecorder, RunBudget
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

CLEAN_PAYLOAD = CatalogIngestPayload(
    supplier=SupplierCandidate(name_text="Sunrise Travel Co", source_quote="Sunrise Travel Co"),
    products=[
        ProductCandidate(
            title_text="Halong Cruise — Deluxe Cabin",
            destination_text="Hanoi",
            category_hint="accommodation",
            source_quote="Halong Cruise Deluxe Cabin",
        )
    ],
    rate_groups=[],
)


class _FakeUsage:
    input_tokens = 0
    output_tokens = 0


async def _fake_extractor(sanitized_text: str) -> tuple[CatalogIngestPayload, _FakeUsage]:
    return CLEAN_PAYLOAD.model_copy(deep=True), _FakeUsage()


async def _fake_resolver(session, tenant_id, payload):
    entries = [
        ResolutionEntry(entity_ref="/supplier", entity_type="supplier", action="create", evidence="new supplier"),
        ResolutionEntry(entity_ref="/products/0", entity_type="product", action="create", evidence="new product"),
    ]
    return ResolutionPlan(entries=entries), AllowlistRecorder(), RunBudget(max_calls=5)


async def _fake_resolver_with_clarification(session, tenant_id, payload):
    from schemas.catalog_ingest import Clarification

    entries = [
        ResolutionEntry(entity_ref="/supplier", entity_type="supplier", action="create", evidence="new supplier"),
        ResolutionEntry(
            entity_ref="/products/0",
            entity_type="product",
            action="needs_input",
            evidence="category_hint is missing",
            clarifications=[
                Clarification(
                    id="product-0-category",
                    question="What category is this?",
                    blocking=True,
                    target_path="/products/0/category_hint",
                )
            ],
        ),
    ]
    return ResolutionPlan(entries=entries), AllowlistRecorder(), RunBudget(max_calls=5)


class IngestionApiTests(unittest.TestCase):
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
        self.extractor_patch = patch.object(extraction_service, "_run_extractor", new=AsyncMock(side_effect=_fake_extractor))
        self.resolver_patch = patch.object(resolution_service, "_run_resolver", new=AsyncMock(side_effect=_fake_resolver))
        self.extractor_patch.start()
        self.resolver_patch.start()
        self.addCleanup(self.extractor_patch.stop)
        self.addCleanup(self.resolver_patch.stop)

    async def _reset_tables(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with self.session_factory() as session:
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            session.add(DestinationAlias(id="dal_hanoi", destination_id="dst_hanoi", normalized_alias="hanoi"))
            await session.commit()

    def test_create_batch_runs_extractor_and_resolver_round_1(self):
        response = self._create_batch()
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["source_channel"], "email")
        self.assertIn(body["status"], {"ready", "needs_clarification", "draft"})
        self.assertEqual(len(body["payload"]["products"]), 1)

    def test_create_batch_is_idempotent_on_same_key(self):
        first = self._create_batch()
        second = self._create_batch()
        self.assertEqual(first.json()["id"], second.json()["id"])

    def test_list_batches_returns_created_batch(self):
        created = self._create_batch()
        listing = self.client.get("/api/v2/ingestion-batches")
        self.assertEqual(listing.status_code, 200)
        ids = [item["id"] for item in listing.json()["items"]]
        self.assertIn(created.json()["id"], ids)

    def test_get_batch_by_id(self):
        created = self._create_batch()
        batch_id = created.json()["id"]
        fetched = self.client.get(f"/api/v2/ingestion-batches/{batch_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["id"], batch_id)

    def test_get_missing_batch_returns_404(self):
        response = self.client.get("/api/v2/ingestion-batches/igb_does_not_exist")
        self.assertEqual(response.status_code, 404)

    def test_reject_batch_transitions_status(self):
        created = self._create_batch()
        batch_id, revision = created.json()["id"], created.json()["batch_revision"]
        rejected = self.client.post(
            f"/api/v2/ingestion-batches/{batch_id}/reject",
            json={"baseBatchRevision": revision, "reason": "duplicate paste"},
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["status"], "rejected")

    def test_reject_with_stale_revision_returns_409(self):
        created = self._create_batch()
        batch_id = created.json()["id"]
        stale_revision = created.json()["batch_revision"] + 5
        response = self.client.post(
            f"/api/v2/ingestion-batches/{batch_id}/reject",
            json={"baseBatchRevision": stale_revision},
        )
        self.assertEqual(response.status_code, 409)

    def test_commit_requires_quote_admin_role(self):
        created = self._create_batch()
        batch_id, revision = created.json()["id"], created.json()["batch_revision"]
        with patch.dict(os.environ, {"DMC_GATEWAY_ENABLED": "true", "QUOTE_ADMIN_ROLES": "quote_admin"}):
            response = self.client.post(
                f"/api/v2/ingestion-batches/{batch_id}/commit",
                json={"baseBatchRevision": revision},
                headers={"Idempotency-Key": "commit-attempt-1", "X-DMC-Email": "editor@capella.travel", "X-DMC-Role": "editor"},
            )
        self.assertEqual(response.status_code, 403)

    def test_commit_missing_idempotency_key_header_returns_422(self):
        created = self._create_batch()
        batch_id, revision = created.json()["id"], created.json()["batch_revision"]
        response = self.client.post(
            f"/api/v2/ingestion-batches/{batch_id}/commit", json={"baseBatchRevision": revision}
        )
        self.assertEqual(response.status_code, 422)

    def test_create_missing_idempotency_key_header_returns_422(self):
        response = self.client.post(
            "/api/v2/ingestion-batches",
            json={"rawText": "text", "sourceChannel": "email", "sourceDocumentType": "rate_sheet"},
        )
        self.assertEqual(response.status_code, 422)

    def test_edit_with_stale_revision_returns_409(self):
        created = self._create_batch()
        batch_id = created.json()["id"]
        stale_revision = created.json()["batch_revision"] + 5
        response = self.client.put(
            f"/api/v2/ingestion-batches/{batch_id}/edits",
            json={"edits": {}, "baseBatchRevision": stale_revision},
        )
        self.assertEqual(response.status_code, 409)

    def test_answer_with_stale_revision_returns_409(self):
        with patch.object(resolution_service, "_run_resolver", new=AsyncMock(side_effect=_fake_resolver_with_clarification)):
            created = self._create_batch(idempotency_key="test-create-clarify")
        self.assertEqual(created.json()["status"], "needs_clarification", created.text)
        batch_id = created.json()["id"]
        stale_revision = created.json()["batch_revision"] + 5
        response = self.client.post(
            f"/api/v2/ingestion-batches/{batch_id}/answers",
            json={"answers": {"product-0-category": "accommodation"}, "baseBatchRevision": stale_revision},
        )
        self.assertEqual(response.status_code, 409)

    def test_answer_resolves_blocking_clarification_and_reaches_ready(self):
        with patch.object(resolution_service, "_run_resolver", new=AsyncMock(side_effect=_fake_resolver_with_clarification)):
            created = self._create_batch(idempotency_key="test-create-clarify-2")
        self.assertEqual(created.json()["status"], "needs_clarification", created.text)
        batch_id, revision = created.json()["id"], created.json()["batch_revision"]
        response = self.client.post(
            f"/api/v2/ingestion-batches/{batch_id}/answers",
            json={"answers": {"product-0-category": "accommodation"}, "baseBatchRevision": revision},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(response.json()["status"], {"ready", "draft"})

    def test_rate_limit_returns_429_after_daily_max(self):
        import routers.v2.ingestion as ingestion_router

        with patch.object(ingestion_router, "MAX_BATCHES_PER_ACTOR_PER_DAY", 1):
            first = self._create_batch(idempotency_key="rate-limit-1")
            self.assertEqual(first.status_code, 201, first.text)
            second = self._create_batch(idempotency_key="rate-limit-2")
        self.assertEqual(second.status_code, 429)

    def _create_batch(self, idempotency_key="test-create-1", **overrides):
        payload = {
            "rawText": "Sunrise Travel Co — Halong Cruise Deluxe Cabin, contact us for rates.",
            "sourceChannel": "email",
            "sourceDocumentType": "rate_sheet",
        }
        payload.update(overrides)
        return self.client.post(
            "/api/v2/ingestion-batches", json=payload, headers={"Idempotency-Key": idempotency_key}
        )

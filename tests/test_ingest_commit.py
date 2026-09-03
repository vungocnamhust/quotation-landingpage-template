import os
import tempfile
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.destination import DestinationAlias, DestinationCatalog
from db.models.product import Product
from db.models.rate import Rate, RatePriceLine
from db.models.supplier import Supplier
from repositories.ingestion_repository import IngestionRepository
from repositories.product_repository import ProductRepository
from repositories.rate_repository import RateRepository
from repositories.supplier_repository import SupplierRepository
from schemas.catalog_ingest import CatalogIngestPayload, ProductCandidate, RateGroupCandidate, PriceLineCandidate, SupplierCandidate
from services.ingestion.commit_service import CommitError, commit_batch
from services.ingestion.extraction_service import parse_payload
from services.product_service import normalize_product_title
from services.supplier_service import normalize_supplier_name

ACTOR = ActorRef(actor_id="operator@capella.travel", actor_type="staff")


def _ready_payload() -> CatalogIngestPayload:
    return CatalogIngestPayload(
        supplier=SupplierCandidate(name_text="Brand New Supplier Co", source_quote="Brand New Supplier Co"),
        products=[
            ProductCandidate(
                title_text="Riverside Villa — Garden View",
                destination_text="Hanoi",
                category_hint="accommodation",
                source_quote="Riverside Villa Garden View",
            )
        ],
        rate_groups=[
            RateGroupCandidate(
                product_title_text="Riverside Villa — Garden View",
                validity_text="01/01/2026 - 31/03/2026",
                source_quote="01/01/2026 - 31/03/2026, adult 1.500.000 VND",
                price_lines=[
                    PriceLineCandidate(
                        price_for_hint="adult",
                        amount_text="1.500.000",
                        currency_text="VND",
                        source_quote="adult 1.500.000 VND",
                    )
                ],
            )
        ],
    )


def _resolution_entries() -> list[dict]:
    return [
        {"entity_ref": "/supplier", "entity_type": "supplier", "action": "create", "matched_id": None, "evidence": "new supplier", "clarifications": []},
        {"entity_ref": "/products/0", "entity_type": "product", "action": "create", "matched_id": None, "evidence": "new product", "clarifications": []},
        {"entity_ref": "/rate_groups/0", "entity_type": "rate", "action": "create", "matched_id": None, "evidence": "new rate", "clarifications": []},
    ]


class IngestCommitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.database_file.close()
        self.engine = make_test_engine(f"sqlite+aiosqlite:///{self.database_file.name}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.session_factory() as session:
            session.add(DestinationCatalog(id="dst_hanoi", canonical_name="Hanoi", slug="hanoi"))
            await session.flush()
            session.add(DestinationAlias(id="dal_hanoi", destination_id="dst_hanoi", normalized_alias="hanoi"))
            await session.commit()
        self.session = self.session_factory()

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()
        os.unlink(self.database_file.name)

    async def _make_ready_batch(self, *, payload=None, entries=None, batch_id="igb_test1", idempotency_key="idem-1"):
        payload = payload or _ready_payload()
        reparsed, parsed = parse_payload(payload)
        repository = IngestionRepository(self.session)
        batch = await repository.insert(
            batch_id=batch_id,
            values={
                "status": "ready",
                "raw_text": "irrelevant for commit test",
                "source_channel": "email",
                "source_document_type": "rate_sheet",
                "payload_json": {"payload": reparsed.model_dump(mode="json"), "parsed": parsed},
                "resolution_json": {"entries": entries if entries is not None else _resolution_entries(), "clarifications": []},
                "conversation_json": [],
                "operator_edits_json": {},
                "idempotency_key": idempotency_key,
                "created_by": ACTOR.serialize(),
                "updated_by": ACTOR.serialize(),
            },
        )
        await self.session.commit()
        return batch

    async def test_commit_creates_supplier_product_rate_and_rate_source(self):
        batch = await self._make_ready_batch()
        committed = await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-1")
        await self.session.commit()

        assert committed.status == "committed"
        result = committed.commit_result_json
        supplier = await SupplierRepository(self.session).get_by_id(result["supplier_id"])
        assert supplier is not None
        assert supplier.created_by == ACTOR.serialize()

        assert len(result["product_ids"]) == 1
        product = await ProductRepository(self.session).get_by_id(result["product_ids"][0])
        assert product is not None
        assert product.supplier_id == result["supplier_id"]

        assert len(result["rate_ids"]) == 1
        rate = await RateRepository(self.session).get_by_id(result["rate_ids"][0])
        assert rate is not None
        assert rate.lifecycle_status == "active"
        assert rate.lines[0].amount_minor == 1_500_000
        assert rate.source_id == result["rate_source_id"]

    async def test_commit_blocked_when_unresolved_items_not_acknowledged(self):
        payload = _ready_payload()
        payload.rate_groups[0].price_lines[0] = PriceLineCandidate(
            price_for_hint="adult", amount_text="liên hệ", source_quote="liên hệ"
        )
        batch = await self._make_ready_batch(payload=payload)
        with self.assertRaises(CommitError):
            await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-2")

    async def test_commit_blocked_when_needs_input_entries_remain(self):
        entries = _resolution_entries()
        entries[1]["action"] = "needs_input"
        batch = await self._make_ready_batch(entries=entries)
        with self.assertRaises(CommitError):
            await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-3")

    async def test_commit_is_idempotent_on_already_committed_batch(self):
        batch = await self._make_ready_batch()
        first = await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-4")
        await self.session.commit()
        second = await commit_batch(self.session, batch=first, actor=ACTOR, expected_revision=first.batch_revision, idempotency_key="commit-4")
        assert second.commit_result_json == first.commit_result_json

        products, total = await ProductRepository(self.session).list(active_only=None)
        assert total == 1  # replay must not create a second product

    async def test_commit_supersede_rate_preserves_old_rate_as_superseded(self):
        """R3 immutability — supersede creates a NEW active rate and marks the old one
        'superseded', it never mutates the old rate's amounts (15.3 chốt R3)."""
        title_normalized = normalize_product_title("Riverside Villa — Garden View")
        name_normalized = normalize_supplier_name("Brand New Supplier Co")
        self.session.add(
            Supplier(
                id="sup_existing",
                name="Brand New Supplier Co",
                name_normalized=name_normalized,
                supplier_type="direct",
                default_currency="VND",
            )
        )
        await self.session.flush()
        self.session.add(
            Product(
                id="prd_existing",
                destination_id="dst_hanoi",
                category="accommodation",
                title="Riverside Villa — Garden View",
                title_normalized=title_normalized,
                supplier_id="sup_existing",
                unit="room",
                time_basis="night",
            )
        )
        await self.session.flush()
        self.session.add(
            Rate(
                id="rat_existing",
                product_id="prd_existing",
                currency="VND",
                rate_basis="net",
                valid_from=date(2026, 1, 1),
                valid_to=date(2026, 2, 28),
                season_name="Old season",
                lifecycle_status="active",
            )
        )
        await self.session.flush()
        self.session.add(RatePriceLine(rate_id="rat_existing", price_for="adult", occupancy_basis="na", unit="person", amount_minor=1_000_000))
        await self.session.commit()

        entries = [
            {"entity_ref": "/supplier", "entity_type": "supplier", "action": "skip_duplicate", "matched_id": "sup_existing", "evidence": "matches existing", "clarifications": []},
            {"entity_ref": "/products/0", "entity_type": "product", "action": "update", "matched_id": "prd_existing", "evidence": "matches existing", "clarifications": []},
            {"entity_ref": "/rate_groups/0", "entity_type": "rate", "action": "supersede_rate", "matched_id": "prd_existing", "evidence": "new season overlaps", "clarifications": []},
        ]
        batch = await self._make_ready_batch(entries=entries)
        committed = await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-supersede")
        await self.session.commit()

        new_rate = await RateRepository(self.session).get_by_id(committed.commit_result_json["rate_ids"][0])
        assert new_rate.lifecycle_status == "active"
        assert new_rate.lines[0].amount_minor == 1_500_000

        old_rate = await RateRepository(self.session).get_by_id("rat_existing")
        assert old_rate.lifecycle_status == "superseded"
        assert old_rate.lines[0].amount_minor == 1_000_000  # untouched, not mutated

    async def test_commit_supplier_update_never_wipes_existing_contact_json(self):
        """H4 — a supplier resolution action of ``update`` must never overwrite the existing
        supplier's real ``contact_json`` with an empty one; the ingest payload carries no
        contact data to write in the first place."""
        title_normalized = normalize_product_title("Riverside Villa — Garden View")
        name_normalized = normalize_supplier_name("Brand New Supplier Co")
        existing_contact = {"person": "Ms. Lan", "email": "lan@existingsupplier.example", "phone": "+84-90-000-0000"}
        self.session.add(
            Supplier(
                id="sup_existing",
                name="Brand New Supplier Co",
                name_normalized=name_normalized,
                supplier_type="direct",
                default_currency="VND",
                contact_json=existing_contact,
            )
        )
        await self.session.flush()
        self.session.add(
            Product(
                id="prd_existing",
                destination_id="dst_hanoi",
                category="accommodation",
                title="Riverside Villa — Garden View",
                title_normalized=title_normalized,
                supplier_id="sup_existing",
                unit="room",
                time_basis="night",
            )
        )
        await self.session.commit()

        entries = [
            {"entity_ref": "/supplier", "entity_type": "supplier", "action": "update", "matched_id": "sup_existing", "evidence": "matches existing", "clarifications": []},
            {"entity_ref": "/products/0", "entity_type": "product", "action": "update", "matched_id": "prd_existing", "evidence": "matches existing", "clarifications": []},
            {"entity_ref": "/rate_groups/0", "entity_type": "rate", "action": "create", "matched_id": None, "evidence": "new rate", "clarifications": []},
        ]
        batch = await self._make_ready_batch(entries=entries)
        committed = await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-supplier-update")
        await self.session.commit()

        assert committed.commit_result_json["supplier_id"] == "sup_existing"
        supplier = await SupplierRepository(self.session).get_by_id("sup_existing")
        assert supplier.contact_json == existing_contact

    async def test_commit_mid_failure_rolls_back_all_writes(self):
        """Chốt #7 — commit is one transaction: a failure partway through (here, a price
        line missing price_for_hint, only caught while building the rate) must leave 0
        catalog records behind, including the supplier/product already written earlier in
        the same call."""
        payload = _ready_payload()
        payload.rate_groups[0].price_lines[0] = PriceLineCandidate(
            amount_text="1.500.000", currency_text="VND", source_quote="1.500.000 VND"
        )  # no price_for_hint -> _price_lines_for raises CommitError
        batch = await self._make_ready_batch(payload=payload)

        with self.assertRaises(CommitError):
            await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-midfail")
        await self.session.rollback()

        suppliers, total = await SupplierRepository(self.session).list(active_only=None)
        assert total == 0, "supplier created earlier in the same failed commit must be rolled back"
        products, total = await ProductRepository(self.session).list(active_only=None)
        assert total == 0, "product created earlier in the same failed commit must be rolled back"

    async def test_commit_converts_raw_rate_integrity_error_to_commit_error_without_poisoning_session(self):
        """RateService (unlike SupplierService/ProductService, Track 1 audit R-M2) has no
        savepoint of its own around its inserts, so a duplicate/conflicting rate can still
        reach commit_batch as a raw IntegrityError from the database driver. This must come
        out as a typed CommitError (422 at the router), and — because commit_batch's own
        begin_nested() rolls back to its savepoint on the way out — the session must stay
        usable afterwards for the *next* commit attempt in the same request/session, with no
        explicit session.rollback() needed first."""
        from unittest.mock import AsyncMock, patch

        from sqlalchemy.exc import IntegrityError

        batch = await self._make_ready_batch()

        with patch(
            "services.rate_service.RateService.create_draft",
            new=AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("duplicate rate"))),
        ):
            with self.assertRaises(CommitError):
                await commit_batch(self.session, batch=batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-rate-conflict")

        # No manual rollback here — proves the outer begin_nested() already recovered the
        # session, unlike test_commit_mid_failure_rolls_back_all_writes above which needs one.
        suppliers, total = await SupplierRepository(self.session).list(active_only=None)
        assert total == 0, "supplier created earlier in the same failed commit must be rolled back"
        products, total = await ProductRepository(self.session).list(active_only=None)
        assert total == 0, "product created earlier in the same failed commit must be rolled back"

        # The session must still accept new work — proof it was never left "poisoned".
        other_batch = await self._make_ready_batch(batch_id="igb_test2", idempotency_key="idem-2")
        committed = await commit_batch(self.session, batch=other_batch, actor=ACTOR, expected_revision=0, idempotency_key="commit-retry-after-conflict")
        await self.session.commit()
        assert committed.status == "committed"

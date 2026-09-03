import asyncio
import os
import tempfile
import unittest

import pydantic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from core.kernel import ActorRef
from db.base import Base
from schemas.v2.supplier import (
    SupplierCancellationPolicySchema,
    SupplierChildPolicySchema,
    SupplierCreateSchema,
    SupplierUpdateSchema,
)
from services.product_service import normalize_product_title
from services.supplier_service import SupplierService, SupplierValidationError, normalize_supplier_name


class NormalizeSupplierNameTests(unittest.TestCase):
    def test_strips_vietnamese_diacritics_and_collapses_spaces(self):
        self.assertEqual(normalize_supplier_name("  Khách Sạn  Mường Thanh "), "khach san muong thanh")

    def test_lowercases(self):
        self.assertEqual(normalize_supplier_name("Saigon DMC"), "saigon dmc")

    def test_folds_dJ_stroke_the_same_as_its_diacritic_free_form(self):
        """Track 1 audit H1: NFD-based stripping never touches đ/Đ (U+0111/U+0110)
        because they have no canonical decomposition — a hand-rolled normalizer that
        only does NFD + strip-Mn silently lets 'Đông Á' and 'Dong A' dedupe as two
        different suppliers, even though they're the same name."""
        self.assertEqual(normalize_supplier_name("Khách sạn Đông Á"), normalize_supplier_name("Khach san Dong A"))
        self.assertEqual(normalize_supplier_name("Hạ Long"), normalize_supplier_name("Ha Long"))
        self.assertEqual(normalize_supplier_name("  Đà  Nẵng "), "da nang")

    def test_is_the_same_function_object_as_product_normalizer(self):
        """Track 1 audit H1/M7: guards against the two normalizers drifting back
        into separate copies of the same algorithm."""
        self.assertIs(normalize_supplier_name, normalize_product_title)


class SupplierCancellationPolicyValidatorTests(unittest.TestCase):
    def test_rejects_overlapping_days(self):
        with self.assertRaises(pydantic.ValidationError):
            SupplierCancellationPolicySchema(
                tiers=[
                    {"days_before_service_min": 7, "penalty_percent": 50},
                    {"days_before_service_min": 7, "penalty_percent": 100},
                ]
            )

    def test_rejects_penalty_not_increasing_as_days_decrease(self):
        with self.assertRaises(pydantic.ValidationError):
            SupplierCancellationPolicySchema(
                tiers=[
                    {"days_before_service_min": 14, "penalty_percent": 80},
                    {"days_before_service_min": 7, "penalty_percent": 50},
                ]
            )

    def test_accepts_well_ordered_tiers(self):
        policy = SupplierCancellationPolicySchema(
            tiers=[
                {"days_before_service_min": 14, "penalty_percent": 30},
                {"days_before_service_min": 7, "penalty_percent": 60},
                {"days_before_service_min": 0, "penalty_percent": 100},
            ]
        )
        self.assertEqual(len(policy.tiers), 3)


class SupplierChildPolicyValidatorTests(unittest.TestCase):
    def test_rejects_overlapping_age_bands(self):
        with self.assertRaises(pydantic.ValidationError):
            SupplierChildPolicySchema(
                bands=[
                    {"age_min": 0, "age_max": 6, "charge_percent": 0},
                    {"age_min": 5, "age_max": 11, "charge_percent": 50},
                ]
            )

    def test_rejects_age_min_greater_than_age_max(self):
        with self.assertRaises(pydantic.ValidationError):
            SupplierChildPolicySchema(bands=[{"age_min": 10, "age_max": 5, "charge_percent": 50}])

    def test_accepts_non_overlapping_bands(self):
        policy = SupplierChildPolicySchema(
            bands=[
                {"age_min": 0, "age_max": 4, "charge_percent": 0},
                {"age_min": 5, "age_max": 11, "charge_percent": 50},
            ]
        )
        self.assertEqual(len(policy.bands), 2)


class SupplierServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = make_test_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)
        asyncio.run(cls._init_db())

    @classmethod
    async def _init_db(cls):
        async with cls.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    @classmethod
    def tearDownClass(cls):
        asyncio.run(cls.engine.dispose())
        os.unlink(cls.db_file.name)

    def setUp(self):
        asyncio.run(self._reset_db())

    async def _reset_db(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    def test_create_writes_actor_ref_to_created_and_updated_by(self):
        async def scenario():
            async with self.session_factory() as session:
                service = SupplierService(session)
                supplier = await service.create_supplier(
                    SupplierCreateSchema(
                        name="Saigon DMC",
                        supplier_type="dmc",
                        default_currency="usd",
                    ),
                    actor=ActorRef(actor_id="staff@example.com", actor_type="staff"),
                )
                await session.commit()

                self.assertEqual(supplier.default_currency, "USD")
                self.assertTrue(supplier.id.startswith("sup_"))

                from repositories.supplier_repository import SupplierRepository

                row = await SupplierRepository(session).get_by_id(supplier.id)
                self.assertEqual(row.created_by, "staff:staff@example.com")
                self.assertEqual(row.updated_by, "staff:staff@example.com")
                self.assertEqual(row.name_normalized, "saigon dmc")

        asyncio.run(scenario())

    def test_duplicate_normalized_name_is_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                service = SupplierService(session)
                actor = ActorRef(actor_id="staff@example.com", actor_type="staff")
                await service.create_supplier(
                    SupplierCreateSchema(name="Hanoi La Siesta", supplier_type="direct", default_currency="USD"),
                    actor=actor,
                )
                await session.commit()

                with self.assertRaisesRegex(ValueError, "already exists"):
                    await service.create_supplier(
                        SupplierCreateSchema(name="  hanoi   la siesta ", supplier_type="direct", default_currency="USD"),
                        actor=actor,
                    )

        asyncio.run(scenario())

    def test_update_recomputes_normalized_name_and_updated_by(self):
        async def scenario():
            async with self.session_factory() as session:
                service = SupplierService(session)
                creator = ActorRef(actor_id="creator@example.com", actor_type="staff")
                supplier = await service.create_supplier(
                    SupplierCreateSchema(name="Old Supplier Name", supplier_type="direct", default_currency="USD"),
                    actor=creator,
                )
                await session.commit()

                editor = ActorRef(actor_id="editor@example.com", actor_type="staff")
                updated = await service.update_supplier(
                    supplier.id,
                    SupplierUpdateSchema(name="New Supplier Name"),
                    actor=editor,
                )
                await session.commit()

                self.assertEqual(updated.name, "New Supplier Name")

                from repositories.supplier_repository import SupplierRepository

                row = await SupplierRepository(session).get_by_id(supplier.id)
                self.assertEqual(row.name_normalized, "new supplier name")
                self.assertEqual(row.updated_by, "staff:editor@example.com")
                self.assertEqual(row.created_by, "staff:creator@example.com")

        asyncio.run(scenario())

    def test_create_with_unknown_destination_id_is_rejected_with_422_not_500(self):
        """Track 1 audit H2: SQLite has no FK enforcement unless PRAGMA foreign_keys=ON
        is set, so this must be caught explicitly in the service, not left to the
        database (which would 500 on Postgres and silently persist on SQLite)."""

        async def scenario():
            async with self.session_factory() as session:
                service = SupplierService(session)
                with self.assertRaises(SupplierValidationError):
                    await service.create_supplier(
                        SupplierCreateSchema(
                            name="Ghost Destination Supplier",
                            supplier_type="direct",
                            default_currency="USD",
                            destination_id="dst_does_not_exist",
                        ),
                        actor=ActorRef(actor_id="staff@example.com", actor_type="staff"),
                    )

        asyncio.run(scenario())

    def test_unsupported_currency_is_422_not_409(self):
        """Track 1 audit M2: SupplierService used to raise plain ValueError for every
        failure, and the router mapped all of them to 409 — including a validation
        error that should be 422."""

        async def scenario():
            async with self.session_factory() as session:
                service = SupplierService(session)
                with self.assertRaises(SupplierValidationError):
                    await service.create_supplier(
                        SupplierCreateSchema(name="Bad Currency Co", supplier_type="direct", default_currency="XYZ"),
                        actor=ActorRef(actor_id="staff@example.com", actor_type="staff"),
                    )

        asyncio.run(scenario())

    def test_blank_name_is_rejected(self):
        """Track 1 audit M3."""
        with self.assertRaises(pydantic.ValidationError):
            SupplierCreateSchema(name="   ", supplier_type="direct", default_currency="USD")

    def test_concurrent_create_with_same_dedupe_key_yields_one_conflict(self):
        """Track 1 audit H3: check-then-insert is a TOCTOU race. Two concurrent
        creates that both pass the pre-check must not both reach the database — the
        loser's IntegrityError must become a typed conflict, not an unhandled 500
        that also poisons the session for the next request."""

        async def scenario():
            from services.supplier_service import SupplierConflictError

            async with self.session_factory() as outer_session:
                service_a = SupplierService(outer_session)
                actor = ActorRef(actor_id="staff@example.com", actor_type="staff")

                async def create():
                    return await service_a.create_supplier(
                        SupplierCreateSchema(name="Race Supplier Co", supplier_type="direct", default_currency="USD"),
                        actor=actor,
                    )

                # Simulate the race deterministically: pre-check passes for both,
                # then the second insert collides on the unique index at flush().
                await create()
                await outer_session.commit()

                with self.assertRaises(SupplierConflictError):
                    async with self.session_factory() as session:
                        service_b = SupplierService(session)
                        # Force the pre-check to look stale, as it would under a real race.
                        from unittest.mock import AsyncMock

                        service_b.repository.get_by_normalized_name = AsyncMock(return_value=None)
                        await service_b.create_supplier(
                            SupplierCreateSchema(
                                name="Race Supplier Co", supplier_type="direct", default_currency="USD"
                            ),
                            actor=actor,
                        )

                # The session must still be usable afterwards (rollback happened).
                async with self.session_factory() as session:
                    service_c = SupplierService(session)
                    other = await service_c.create_supplier(
                        SupplierCreateSchema(name="Unrelated Supplier Co", supplier_type="direct", default_currency="USD"),
                        actor=actor,
                    )
                    await session.commit()
                    self.assertTrue(other.id.startswith("sup_"))

        asyncio.run(scenario())

    def test_pagination_total_reflects_full_filtered_count_not_page_size(self):
        """Track 1 audit H4."""

        async def scenario():
            async with self.session_factory() as session:
                service = SupplierService(session)
                actor = ActorRef(actor_id="staff@example.com", actor_type="staff")
                for i in range(5):
                    await service.create_supplier(
                        SupplierCreateSchema(name=f"Paginated Supplier {i}", supplier_type="direct", default_currency="USD"),
                        actor=actor,
                    )
                await session.commit()

                items, total = await service.list_suppliers(limit=2)
                self.assertEqual(len(items), 2)
                self.assertEqual(total, 5)

        asyncio.run(scenario())

    def test_search_with_diacritics_finds_diacritic_stripped_normalized_name(self):
        """Track 1 audit H5."""

        async def scenario():
            async with self.session_factory() as session:
                service = SupplierService(session)
                await service.create_supplier(
                    SupplierCreateSchema(name="Điểm Đến Á Đông", supplier_type="direct", default_currency="USD"),
                    actor=ActorRef(actor_id="staff@example.com", actor_type="staff"),
                )
                await session.commit()

                items, total = await service.list_suppliers(search="Điểm")
                self.assertEqual(total, 1)
                self.assertEqual(items[0].name, "Điểm Đến Á Đông")

        asyncio.run(scenario())

    def test_create_supplier_rejects_merged_and_inactive_destinations(self):
        """Track 1 audit R-H2: validate destination liveness (merged & inactive rejection)."""
        from repositories.destination_repository import DestinationRepository

        async def scenario():
            async with self.session_factory() as session:
                dest_repo = DestinationRepository(session)
                live_dest = await dest_repo.create(
                    destination_id="dst_live_hub",
                    canonical_name="Live Hub",
                    slug="live-hub",
                    aliases=[],
                    country_slug="vietnam",
                    region_slug="central",
                    province_slug="quang-nam",
                    latitude=15.88,
                    longitude=108.33,
                )
                inactive_dest = await dest_repo.create(
                    destination_id="dst_inactive_hub",
                    canonical_name="Inactive Hub",
                    slug="inactive-hub",
                    aliases=[],
                    country_slug="vietnam",
                    region_slug="central",
                    province_slug="quang-nam",
                    latitude=15.89,
                    longitude=108.34,
                )
                await dest_repo.set_status(inactive_dest, is_active=False)

                source_dest = await dest_repo.create(
                    destination_id="dst_source_hub",
                    canonical_name="Source Hub",
                    slug="source-hub",
                    aliases=[],
                    country_slug="vietnam",
                    region_slug="central",
                    province_slug="quang-nam",
                    latitude=15.90,
                    longitude=108.35,
                )
                await dest_repo.merge(source_id="dst_source_hub", target_id="dst_live_hub")
                await session.commit()

            actor = ActorRef(actor_id="staff@example.com", actor_type="staff")

            # 1. Pointing to merged destination -> 422 with merged_into_id
            async with self.session_factory() as session:
                service = SupplierService(session)
                with self.assertRaises(SupplierValidationError) as ctx:
                    await service.create_supplier(
                        SupplierCreateSchema(
                            name="Supplier Merged Target",
                            supplier_type="direct",
                            default_currency="USD",
                            destination_id="dst_source_hub",
                        ),
                        actor=actor,
                    )
                self.assertIn("has been merged into 'dst_live_hub'", str(ctx.exception))

            # 2. Pointing to inactive destination -> 422 inactive
            async with self.session_factory() as session:
                service = SupplierService(session)
                with self.assertRaises(SupplierValidationError) as ctx:
                    await service.create_supplier(
                        SupplierCreateSchema(
                            name="Supplier Inactive Target",
                            supplier_type="direct",
                            default_currency="USD",
                            destination_id="dst_inactive_hub",
                        ),
                        actor=actor,
                    )
                self.assertIn("is inactive", str(ctx.exception))

            # 3. Pointing to active live destination -> 201/success
            async with self.session_factory() as session:
                service = SupplierService(session)
                created = await service.create_supplier(
                    SupplierCreateSchema(
                        name="Supplier Live Target",
                        supplier_type="direct",
                        default_currency="USD",
                        destination_id="dst_live_hub",
                    ),
                    actor=actor,
                )
                await session.commit()
                self.assertEqual(created.destination_id, "dst_live_hub")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()


import asyncio
import os
import tempfile
import unittest

import pydantic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.kernel import ActorRef
from db.base import Base
from schemas.v2.supplier import (
    SupplierCancellationPolicySchema,
    SupplierChildPolicySchema,
    SupplierCreateSchema,
    SupplierUpdateSchema,
)
from services.supplier_service import SupplierService, normalize_supplier_name


class NormalizeSupplierNameTests(unittest.TestCase):
    def test_strips_vietnamese_diacritics_and_collapses_spaces(self):
        self.assertEqual(normalize_supplier_name("  Khách Sạn  Mường Thanh "), "khach san muong thanh")

    def test_lowercases(self):
        self.assertEqual(normalize_supplier_name("Saigon DMC"), "saigon dmc")


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
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
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


if __name__ == "__main__":
    unittest.main()

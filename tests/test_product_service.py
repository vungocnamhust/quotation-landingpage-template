import asyncio
import os
import tempfile
import unittest

import pydantic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.accommodation import AccommodationProfile
from db.models.destination import DestinationCatalog
from schemas.v2.product import ProductCreateSchema, ProductUpdateSchema
from services.product_service import (
    ProductConflictError,
    ProductService,
    ProductValidationError,
    normalize_product_title,
)

ACTOR = ActorRef(actor_id="staff@example.com", actor_type="staff")


class NormalizeProductTitleTests(unittest.TestCase):
    def test_strips_diacritics_and_collapses_spaces(self):
        self.assertEqual(normalize_product_title("  Khách Sạn  Mường Thanh "), "khach san muong thanh")


class ProductServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        cls.db_file.close()
        cls.engine = create_async_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
        cls.session_factory = async_sessionmaker(cls.engine, class_=AsyncSession, expire_on_commit=False)

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
                AccommodationProfile(
                    id="acc_hue_hotel",
                    destination_id="dst_hue",
                    storage_slug="hue-hotel",
                    asset_prefix="hue/hue-hotel",
                    name="Hue Hotel",
                )
            )
            await session.commit()

    def test_create_fills_default_charge_unit_when_omitted(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="accommodation",
                        title="La Siesta Old Quarter",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(product.unit, "room")
                self.assertEqual(product.time_basis, "night")
                self.assertTrue(product.id.startswith("prd_"))
                self.assertIsNone(product.supplier_id)

        asyncio.run(scenario())

    def test_dedupe_same_title_different_supplier_is_allowed(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="transportation",
                        title="4-Seat Car Airport Transfer",
                        supplier_id=None,
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="transportation",
                        title="4-Seat Car Airport Transfer",
                        supplier_id="sup_other",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(product.title, "4-Seat Car Airport Transfer")

        asyncio.run(scenario())

    def test_dedupe_same_four_components_rejected_with_409_style_error(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="ticket",
                        title="Old Quarter Walking Tour",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                with self.assertRaises(ProductConflictError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            category="ticket",
                            title="  old   quarter walking tour ",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_dedupe_null_supplier_twice_is_rejected_via_coalesce(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="meal",
                        title="Welcome Dinner",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                with self.assertRaises(ProductConflictError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            category="meal",
                            title="Welcome Dinner",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_property_id_rejected_when_category_is_not_accommodation(self):
        # Caught by the ProductCreateSchema validator boundary, before the
        # service layer ever runs (schema/v2/product.py::_validate_boundaries).
        with self.assertRaises(pydantic.ValidationError):
            ProductCreateSchema(
                destination_id="dst_hanoi",
                category="ticket",
                title="Wrong Category Property",
                property_id="acc_la_siesta",
            )

    def test_property_id_rejected_when_destination_mismatch(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hue",
                            category="accommodation",
                            title="Mismatched Destination",
                            property_id="acc_la_siesta",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_property_id_accepted_when_category_and_destination_match(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="accommodation",
                        title="La Siesta Deluxe Room",
                        property_id="acc_la_siesta",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(product.property_id, "acc_la_siesta")

        asyncio.run(scenario())

    def test_supplier_product_name_is_immutable(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="guide",
                        title="Local Guide - English",
                        supplier_product_name="Original Source Name",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                with self.assertRaises(ProductValidationError):
                    await service.update_product(
                        product.id,
                        ProductUpdateSchema(supplier_product_name="Changed Name"),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_actor_ref_written_to_created_and_updated_by(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="guide",
                        title="Full Trip Guide",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                from repositories.product_repository import ProductRepository

                row = await ProductRepository(session).get_by_id(product.id)
                self.assertEqual(row.created_by, "staff:staff@example.com")
                self.assertEqual(row.updated_by, "staff:staff@example.com")

        asyncio.run(scenario())

    def test_subcategory_invalid_for_category_is_rejected_with_valid_options(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaisesRegex(ProductValidationError, "hotel"):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            category="accommodation",
                            subcategory="car_4_seat",
                            title="Bad Subcategory Product",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_subcategory_valid_in_other_category_but_wrong_here_is_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                # 'hotel' is valid for accommodation, not for transportation.
                with self.assertRaises(ProductValidationError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            category="transportation",
                            subcategory="hotel",
                            title="Wrong Category Subcategory",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_subcategory_note_without_other_subcategory_is_rejected(self):
        with self.assertRaises(Exception):
            ProductCreateSchema(
                destination_id="dst_hanoi",
                category="accommodation",
                subcategory="hotel",
                subcategory_note="A free-text note",
                title="Note Without Other",
            )

    def test_subcategory_note_with_other_subcategory_is_accepted(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="accommodation",
                        subcategory="other_overnight_accommodation",
                        subcategory_note="Floating bungalow on Ha Long Bay",
                        title="Floating Bungalow",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(product.subcategory_note, "Floating bungalow on Ha Long Bay")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()

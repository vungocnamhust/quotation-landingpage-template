import asyncio
import os
import tempfile
import unittest

import pydantic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.accommodation import AccommodationProfile
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
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
        cls.engine = make_test_engine(f"sqlite+aiosqlite:///{cls.db_file.name}")
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
            await session.flush()
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
            session.add(
                Supplier(
                    id="sup_other",
                    name="Other Supplier Co",
                    name_normalized="other supplier co",
                    supplier_type="dmc",
                    default_currency="USD",
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
        # Track 1 audit H6: this combo check now runs in the service against the
        # merged (existing + payload) state, not at schema construction time, so a
        # partial PUT that only changes subcategory can see the note that's
        # already on the row. See the test_put_*_subcategory* cases below for the
        # PUT-specific merged-state scenarios.
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            category="accommodation",
                            subcategory="hotel",
                            subcategory_note="A free-text note",
                            title="Note Without Other",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

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

    def test_origin_destination_id_rejected_outside_transportation_and_flights(self):
        with self.assertRaises(Exception):
            ProductCreateSchema(
                destination_id="dst_hue",
                origin_destination_id="dst_hanoi",
                category="accommodation",
                title="La Siesta with an origin leg",
            )

    def test_origin_destination_id_accepted_for_transportation(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hue",
                        origin_destination_id="dst_hanoi",
                        category="transportation",
                        title="Hanoi to Hue Overnight Bus",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(product.origin_destination_id, "dst_hanoi")

        asyncio.run(scenario())

    def test_same_title_and_destination_with_different_origin_is_allowed(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hue",
                        origin_destination_id="dst_hanoi",
                        category="transportation",
                        title="16-Seat Van Transfer",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                other_leg = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hue",
                        category="transportation",
                        title="16-Seat Van Transfer",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertIsNone(other_leg.origin_destination_id)

                with self.assertRaises(ProductConflictError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hue",
                            origin_destination_id="dst_hanoi",
                            category="transportation",
                            title="16-Seat Van Transfer",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_update_to_add_origin_outside_allowed_category_is_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="accommodation",
                        title="La Siesta Old Quarter Update Target",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                with self.assertRaises(ProductValidationError):
                    await service.update_product(
                        product.id,
                        ProductUpdateSchema(origin_destination_id="dst_hue"),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_create_with_unknown_destination_supplier_or_origin_is_422_not_500(self):
        """Track 1 audit H2."""

        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_does_not_exist",
                            category="ticket",
                            title="Ghost Destination Ticket",
                        ),
                        actor=ACTOR,
                    )
                with self.assertRaises(ProductValidationError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            category="ticket",
                            title="Ghost Supplier Ticket",
                            supplier_id="sup_does_not_exist",
                        ),
                        actor=ACTOR,
                    )
                with self.assertRaises(ProductValidationError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hue",
                            origin_destination_id="dst_does_not_exist",
                            category="transportation",
                            title="Ghost Origin Bus",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_origin_destination_id_equal_to_destination_id_is_rejected(self):
        """Track 1 audit M4."""

        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError):
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            origin_destination_id="dst_hanoi",
                            category="transportation",
                            title="Hanoi to Hanoi Nonsense Transfer",
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_blank_title_is_rejected(self):
        """Track 1 audit M3."""
        with self.assertRaises(pydantic.ValidationError):
            ProductCreateSchema(destination_id="dst_hanoi", category="ticket", title="   ")

    def test_concurrent_create_with_same_dedupe_key_yields_one_conflict(self):
        """Track 1 audit H3."""

        async def scenario():
            from unittest.mock import AsyncMock

            async with self.session_factory() as session:
                service = ProductService(session)
                await service.create_product(
                    ProductCreateSchema(destination_id="dst_hanoi", category="ticket", title="Race Ticket"),
                    actor=ACTOR,
                )
                await session.commit()

            with self.assertRaises(ProductConflictError):
                async with self.session_factory() as session:
                    service = ProductService(session)
                    service.repository.find_dedupe_conflict = AsyncMock(return_value=None)
                    await service.create_product(
                        ProductCreateSchema(destination_id="dst_hanoi", category="ticket", title="Race Ticket"),
                        actor=ACTOR,
                    )

            # Session usable afterwards for an unrelated request.
            async with self.session_factory() as session:
                service = ProductService(session)
                other = await service.create_product(
                    ProductCreateSchema(destination_id="dst_hanoi", category="ticket", title="Unrelated Ticket"),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertTrue(other.id.startswith("prd_"))

        asyncio.run(scenario())

    def test_pagination_total_reflects_full_filtered_count_not_page_size(self):
        """Track 1 audit H4."""

        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                for i in range(5):
                    await service.create_product(
                        ProductCreateSchema(destination_id="dst_hanoi", category="ticket", title=f"Paginated Ticket {i}"),
                        actor=ACTOR,
                    )
                await session.commit()

                items, total = await service.list_products(limit=2)
                self.assertEqual(len(items), 2)
                self.assertEqual(total, 5)

        asyncio.run(scenario())

    def test_search_with_diacritics_finds_diacritic_stripped_normalized_title(self):
        """Track 1 audit H5."""

        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                await service.create_product(
                    ProductCreateSchema(destination_id="dst_hanoi", category="ticket", title="Điểm Đến Á Đông Tour"),
                    actor=ACTOR,
                )
                await session.commit()

                items, total = await service.list_products(search="Điểm")
                self.assertEqual(total, 1)
                self.assertEqual(items[0].title, "Điểm Đến Á Đông Tour")

        asyncio.run(scenario())

    def test_put_only_subcategory_note_on_existing_other_star_product_is_accepted(self):
        """Track 1 audit H6, bug (a): a partial PUT that sends only subcategory_note
        must be validated against the *existing* subcategory, not None."""

        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="accommodation",
                        subcategory="other_overnight_accommodation",
                        subcategory_note="Original note",
                        title="Floating Bungalow For H6",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                updated = await service.update_product(
                    product.id,
                    ProductUpdateSchema(subcategory_note="Updated note"),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(updated.subcategory_note, "Updated note")

        asyncio.run(scenario())

    def test_put_changing_subcategory_away_from_other_star_without_clearing_note_is_rejected(self):
        """Track 1 audit H6, bug (b): changing subcategory off other_* while a stale
        note is still on the row must not silently persist an invalid combination."""

        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="accommodation",
                        subcategory="other_overnight_accommodation",
                        subcategory_note="Floating bungalow",
                        title="Floating Bungalow For H6b",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                with self.assertRaises(ProductValidationError):
                    await service.update_product(
                        product.id,
                        ProductUpdateSchema(subcategory="hotel"),
                        actor=ACTOR,
                    )

                # And the persisted row must be untouched — no invalid combo saved.
                from repositories.product_repository import ProductRepository

                row = await ProductRepository(session).get_by_id(product.id)
                self.assertEqual(row.subcategory, "other_overnight_accommodation")
                self.assertEqual(row.subcategory_note, "Floating bungalow")

        asyncio.run(scenario())

    def test_put_changing_subcategory_away_from_other_star_and_clearing_note_together_is_accepted(self):
        """Track 1 audit H6."""

        async def scenario():
            async with self.session_factory() as session:
                service = ProductService(session)
                product = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="accommodation",
                        subcategory="other_overnight_accommodation",
                        subcategory_note="Floating bungalow",
                        title="Floating Bungalow For H6c",
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                updated = await service.update_product(
                    product.id,
                    ProductUpdateSchema(subcategory="hotel", subcategory_note=None),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(updated.subcategory, "hotel")
                self.assertIsNone(updated.subcategory_note)

        asyncio.run(scenario())

    def test_create_product_rejects_merged_and_inactive_destinations(self):
        """Track 1 audit R-H2: validate product destination liveness (merged & inactive rejection)."""
        from repositories.destination_repository import DestinationRepository

        async def scenario():
            async with self.session_factory() as session:
                dest_repo = DestinationRepository(session)
                live_dest = await dest_repo.create(
                    destination_id="dst_live_prd_hub",
                    canonical_name="Live Prd Hub",
                    slug="live-prd-hub",
                    aliases=[],
                    country_slug="vietnam",
                    region_slug="central",
                    province_slug="quang-nam",
                    latitude=15.88,
                    longitude=108.33,
                )
                inactive_dest = await dest_repo.create(
                    destination_id="dst_inactive_prd_hub",
                    canonical_name="Inactive Prd Hub",
                    slug="inactive-prd-hub",
                    aliases=[],
                    country_slug="vietnam",
                    region_slug="central",
                    province_slug="quang-nam",
                    latitude=15.89,
                    longitude=108.34,
                )
                await dest_repo.set_status(inactive_dest, is_active=False)

                source_dest = await dest_repo.create(
                    destination_id="dst_source_prd_hub",
                    canonical_name="Source Prd Hub",
                    slug="source-prd-hub",
                    aliases=[],
                    country_slug="vietnam",
                    region_slug="central",
                    province_slug="quang-nam",
                    latitude=15.90,
                    longitude=108.35,
                )
                await dest_repo.merge(source_id="dst_source_prd_hub", target_id="dst_live_prd_hub")
                await session.commit()

            # 1. destination_id merged -> 422 with merged_into_id
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError) as ctx:
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_source_prd_hub",
                            category="ticket",
                            title="Merged Destination Ticket",
                        ),
                        actor=ACTOR,
                    )
                self.assertIn("has been merged into 'dst_live_prd_hub'", str(ctx.exception))

            # 2. destination_id inactive -> 422
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError) as ctx:
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_inactive_prd_hub",
                            category="ticket",
                            title="Inactive Destination Ticket",
                        ),
                        actor=ACTOR,
                    )
                self.assertIn("is inactive", str(ctx.exception))

            # 3. origin_destination_id merged -> 422
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError) as ctx:
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            origin_destination_id="dst_source_prd_hub",
                            category="transportation",
                            title="Merged Origin Bus",
                        ),
                        actor=ACTOR,
                    )
                self.assertIn("has been merged into 'dst_live_prd_hub'", str(ctx.exception))

            # 4. origin_destination_id inactive -> 422
            async with self.session_factory() as session:
                service = ProductService(session)
                with self.assertRaises(ProductValidationError) as ctx:
                    await service.create_product(
                        ProductCreateSchema(
                            destination_id="dst_hanoi",
                            origin_destination_id="dst_inactive_prd_hub",
                            category="transportation",
                            title="Inactive Origin Bus",
                        ),
                        actor=ACTOR,
                    )
                self.assertIn("is inactive", str(ctx.exception))

            # 5. active target -> success
            async with self.session_factory() as session:
                service = ProductService(session)
                created = await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_live_prd_hub",
                        category="ticket",
                        title="Live Target Ticket",
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                self.assertEqual(created.destination_id, "dst_live_prd_hub")

        asyncio.run(scenario())

    def test_create_product_savepoint_preserves_outer_transaction_on_conflict(self):
        """Track 1 audit R-M2: SAVEPOINT prevents session.rollback from destroying outer writes."""
        from unittest.mock import patch
        from sqlalchemy.exc import IntegrityError
        from repositories.supplier_repository import SupplierRepository
        from db.models.supplier import Supplier

        async def scenario():
            async with self.session_factory() as session:
                # 1. Outer write in this session: create a supplier
                sup_repo = SupplierRepository(session)
                await sup_repo.insert(
                    supplier_id="sup_outer_test",
                    values={
                        "name": "Outer Write Supplier",
                        "name_normalized": "outer write supplier",
                        "supplier_type": "dmc",
                        "default_currency": "USD",
                        "created_by": "staff:tester",
                        "updated_by": "staff:tester",
                    },
                )
                await session.flush()

                # 2. Existing product to cause dedupe conflict
                service = ProductService(session)
                await service.create_product(
                    ProductCreateSchema(
                        destination_id="dst_hanoi",
                        category="ticket",
                        title="Conflict Ticket",
                        supplier_id="sup_outer_test",
                    ),
                    actor=ACTOR,
                )
                await session.flush()

                # 3. Simulate IntegrityError inside create_product
                with self.assertRaises(ProductConflictError):
                    with patch.object(service.repository, "insert", side_effect=IntegrityError("stmt", {}, Exception())):
                        await service.create_product(
                            ProductCreateSchema(
                                destination_id="dst_hanoi",
                                category="ticket",
                                title="Another Ticket",
                                supplier_id="sup_outer_test",
                            ),
                            actor=ACTOR,
                        )

                # 4. Outer session is NOT rolled back! The supplier and prod1 can be committed!
                await session.commit()

            # Verify in a new session that the outer write (sup_outer_test) was indeed committed
            async with self.session_factory() as session:
                persisted_sup = await session.get(Supplier, "sup_outer_test")
                self.assertIsNotNone(persisted_sup)
                self.assertEqual(persisted_sup.name, "Outer Write Supplier")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()



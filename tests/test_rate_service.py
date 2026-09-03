import asyncio
import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.kernel import ActorRef
from db.base import Base
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from schemas.v2.product import ProductCreateSchema
from schemas.v2.rate import RateCreateSchema, RatePriceLineCreateSchema, RateSupersedeSchema
from services.product_service import ProductService
from services.rate_service import RateConflictError, RateService, RateValidationError

ACTOR = ActorRef(actor_id="staff@example.com", actor_type="staff")


def _line(**overrides):
    defaults = dict(price_for="adult", occupancy_basis="na", unit="person", amount_minor=1_000_000)
    defaults.update(overrides)
    return RatePriceLineCreateSchema(**defaults)


class RateServiceTests(unittest.TestCase):
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
            product_service = ProductService(session)
            await product_service.create_product(
                ProductCreateSchema(
                    destination_id="dst_hanoi",
                    category="accommodation",
                    title="La Siesta Old Quarter — Deluxe Room",
                    supplier_id="sup_la_siesta",
                ),
                actor=ACTOR,
            )
            await session.commit()

    async def _get_product_id(self, session):
        from repositories.product_repository import ProductRepository

        products, _ = await ProductRepository(session).list(active_only=None, limit=10)
        return products[0].id

    def _base_payload(self, **overrides):
        defaults = dict(
            product_id="prd_placeholder",
            rate_basis="net",
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 3, 31),
            season_name="Winter 2026",
            lines=[_line()],
        )
        defaults.update(overrides)
        return RateCreateSchema(**defaults)

    def test_create_draft_defaults_currency_from_supplier(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                rate = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()
                self.assertEqual(rate.currency, "USD")
                self.assertEqual(rate.lifecycle_status, "draft")
                self.assertEqual(rate.version, 1)
                self.assertTrue(rate.id.startswith("rat_"))
                self.assertEqual(len(rate.lines), 1)

        asyncio.run(scenario())

    def test_full_lifecycle_draft_active_superseded(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()

                activated = await service.activate(v1.id, actor=ACTOR)
                await session.commit()
                self.assertEqual(activated.lifecycle_status, "active")

                supersede_payload = RateSupersedeSchema(
                    rate_basis="net",
                    valid_from=date(2026, 4, 1),
                    valid_to=date(2026, 6, 30),
                    season_name="Summer 2026",
                    lines=[_line(amount_minor=1_200_000)],
                )
                v2 = await service.supersede(v1.id, supersede_payload, actor=ACTOR)
                await session.commit()

                self.assertEqual(v2.lifecycle_status, "active")
                self.assertEqual(v2.version, 2)
                self.assertEqual(v2.supersedes_rate_id, v1.id)

                # R3: reading v1 again — untouched except lifecycle_status
                v1_reloaded = await service.get_rate(v1.id)
                self.assertEqual(v1_reloaded.lifecycle_status, "superseded")
                self.assertEqual(v1_reloaded.valid_from, date(2026, 1, 1))
                self.assertEqual(v1_reloaded.valid_to, date(2026, 3, 31))
                self.assertEqual(v1_reloaded.lines[0].amount_minor, 1_000_000)

        asyncio.run(scenario())

    def test_put_on_active_rate_returns_conflict(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()
                await service.activate(v1.id, actor=ACTOR)
                await session.commit()

                with self.assertRaises(RateConflictError):
                    await service.update_draft(v1.id, self._base_payload(season_name="Edited"), actor=ACTOR)

        asyncio.run(scenario())

    def test_supersede_only_allowed_on_active_rate(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                draft = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()

                with self.assertRaises(RateConflictError):
                    await service.supersede(
                        draft.id,
                        RateSupersedeSchema(
                            rate_basis="net", valid_from=date(2026, 4, 1), valid_to=date(2026, 6, 30), lines=[_line()]
                        ),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_hard_delete_only_allowed_for_draft(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()
                await service.activate(v1.id, actor=ACTOR)
                await session.commit()

                with self.assertRaises(RateConflictError):
                    await service.delete_draft(v1.id)

        asyncio.run(scenario())

    def test_hard_delete_draft_succeeds(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                draft = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()

                deleted = await service.delete_draft(draft.id)
                await session.commit()
                self.assertTrue(deleted)
                self.assertIsNone(await service.get_rate(draft.id))

        asyncio.run(scenario())

    def test_activate_requires_price_lines(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                draft = await service.create_draft(product_id, self._base_payload(lines=[]), actor=ACTOR)
                await session.commit()

                with self.assertRaises(RateValidationError):
                    await service.activate(draft.id, actor=ACTOR)

        asyncio.run(scenario())

    def test_activate_requires_commission_pct_when_gross_commissionable(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                draft = await service.create_draft(
                    product_id, self._base_payload(rate_basis="gross_commissionable"), actor=ACTOR
                )
                await session.commit()

                with self.assertRaises(RateValidationError):
                    await service.activate(draft.id, actor=ACTOR)

        asyncio.run(scenario())

    def test_overlap_between_two_active_rates_flags_but_does_not_block(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()
                await service.activate(v1.id, actor=ACTOR)
                await session.commit()

                overlapping = await service.create_draft(
                    product_id,
                    self._base_payload(valid_from=date(2026, 3, 1), valid_to=date(2026, 5, 31)),
                    actor=ACTOR,
                )
                await session.commit()
                activated = await service.activate(overlapping.id, actor=ACTOR)
                await session.commit()

                self.assertEqual(activated.lifecycle_status, "active")
                self.assertIn("OVERLAP_ACTIVE_RATE", activated.validation_flags_json)

        asyncio.run(scenario())

    def test_inherits_supplier_policy_when_rate_policy_is_null(self):
        async def scenario():
            async with self.session_factory() as session:
                # give the supplier a payment terms default
                from repositories.supplier_repository import SupplierRepository

                supplier_repo = SupplierRepository(session)
                supplier = await supplier_repo.get_by_id("sup_la_siesta")
                supplier.payment_terms_json = {"deposit_percent": 30, "method": "bank_transfer"}
                await session.commit()

                product_id = await self._get_product_id(session)
                service = RateService(session)
                draft = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()

                self.assertIsNone(draft.payment_terms_json)
                self.assertEqual(draft.resolved_payment_terms_json["deposit_percent"], 30)
                self.assertTrue(draft.inherited_from_supplier["payment_terms"])

        asyncio.run(scenario())

    def test_version_increments_across_supersede_chain(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()
                await service.activate(v1.id, actor=ACTOR)
                await session.commit()

                v2 = await service.supersede(
                    v1.id,
                    RateSupersedeSchema(
                        rate_basis="net", valid_from=date(2026, 4, 1), valid_to=date(2026, 6, 30), lines=[_line()]
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                v3 = await service.supersede(
                    v2.id,
                    RateSupersedeSchema(
                        rate_basis="net", valid_from=date(2026, 7, 1), valid_to=date(2026, 9, 30), lines=[_line()]
                    ),
                    actor=ACTOR,
                )
                await session.commit()

                self.assertEqual([v1.version, v2.version, v3.version], [1, 2, 3])

        asyncio.run(scenario())

    def test_update_draft_response_reflects_replaced_lines(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                draft = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()

                updated = await service.update_draft(
                    draft.id,
                    self._base_payload(
                        lines=[_line(amount_minor=111), _line(price_for="child", amount_minor=222)],
                    ),
                    actor=ACTOR,
                )
                self.assertEqual([(line.price_for, line.amount_minor) for line in updated.lines], [("adult", 111), ("child", 222)])

        asyncio.run(scenario())

    def test_source_supplier_must_match_product_supplier(self):
        async def scenario():
            async with self.session_factory() as session:
                session.add(
                    Supplier(
                        id="sup_other",
                        name="Other Supplier",
                        name_normalized="other supplier",
                        supplier_type="direct",
                        default_currency="USD",
                    )
                )
                await session.commit()
                product_id = await self._get_product_id(session)
                with self.assertRaises(RateValidationError):
                    await RateService(session).create_draft(
                        product_id,
                        self._base_payload(source={"supplier_id": "sup_other"}),
                        actor=ACTOR,
                    )

        asyncio.run(scenario())

    def test_concurrent_activate_emits_exactly_one_event(self):
        async def scenario():
            product_id: str
            draft_id: str
            async with self.session_factory() as setup_session:
                product_id = await self._get_product_id(setup_session)
                draft = await RateService(setup_session).create_draft(product_id, self._base_payload(), actor=ACTOR)
                draft_id = draft.id
                await setup_session.commit()

            async with self.session_factory() as session_a:
                service_a = RateService(session_a)
                await service_a.repository.get_by_id(draft_id)
                await session_a.commit()
                async with self.session_factory() as session_b:
                    await RateService(session_b).activate(draft_id, actor=ACTOR)
                    await session_b.commit()

                with self.assertRaises(RateConflictError):
                    await service_a.activate(draft_id, actor=ACTOR)
                await session_a.rollback()

            from db.models.outbox import OutboxEvent
            from sqlalchemy import select

            async with self.session_factory() as verify_session:
                events = list(
                    (await verify_session.scalars(select(OutboxEvent).where(OutboxEvent.aggregate_id == draft_id))).all()
                )
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].event_type, "catalog.rate.activated")

        asyncio.run(scenario())

    def test_concurrent_supersede_second_writer_gets_conflict(self):
        async def scenario():
            async with self.session_factory() as setup_session:
                product_id = await self._get_product_id(setup_session)
                service = RateService(setup_session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await setup_session.commit()
                await service.activate(v1.id, actor=ACTOR)
                await setup_session.commit()
                rate_id = v1.id

            payload = RateSupersedeSchema(
                rate_basis="net", valid_from=date(2026, 4, 1), valid_to=date(2026, 6, 30), lines=[_line()]
            )
            async with self.session_factory() as session_a:
                service_a = RateService(session_a)
                await service_a.repository.get_by_id(rate_id)
                await session_a.commit()
                async with self.session_factory() as session_b:
                    winner = await RateService(session_b).supersede(rate_id, payload, actor=ACTOR)
                    await session_b.commit()
                    self.assertEqual(winner.version, 2)
                with self.assertRaises(RateConflictError):
                    await service_a.supersede(rate_id, payload, actor=ACTOR)
                await session_a.rollback()

            async with self.session_factory() as verify_session:
                rates = await RateService(verify_session).repository.list_active_for_product(product_id)
                self.assertEqual([(rate.version, rate.supersedes_rate_id) for rate in rates], [(2, rate_id)])

        asyncio.run(scenario())

    def test_supersede_failure_rolls_back_predecessor_transition(self):
        async def scenario():
            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()
                await service.activate(v1.id, actor=ACTOR)
                await session.commit()

                with patch.object(service.repository, "replace_lines", side_effect=RuntimeError("injected failure")):
                    with self.assertRaisesRegex(RuntimeError, "injected failure"):
                        await service.supersede(
                            v1.id,
                            RateSupersedeSchema(
                                rate_basis="net", valid_from=date(2026, 4, 1), valid_to=date(2026, 6, 30), lines=[_line()]
                            ),
                            actor=ACTOR,
                        )
                await session.rollback()

                old = await service.get_rate(v1.id)
                self.assertEqual(old.lifecycle_status, "active")
                active = await service.repository.list_active_for_product(product_id)
                self.assertEqual([rate.id for rate in active], [v1.id])

        asyncio.run(scenario())

    def test_superseded_event_payload_is_float_free(self):
        def has_float(value):
            if isinstance(value, float):
                return True
            if isinstance(value, dict):
                return any(has_float(item) for item in value.values())
            if isinstance(value, (list, tuple)):
                return any(has_float(item) for item in value)
            return False

        async def scenario():
            from db.models.outbox import OutboxEvent
            from sqlalchemy import select

            async with self.session_factory() as session:
                product_id = await self._get_product_id(session)
                service = RateService(session)
                v1 = await service.create_draft(product_id, self._base_payload(), actor=ACTOR)
                await session.commit()
                await service.activate(v1.id, actor=ACTOR)
                await session.commit()
                await service.supersede(
                    v1.id,
                    RateSupersedeSchema(
                        rate_basis="net", valid_from=date(2026, 4, 1), valid_to=date(2026, 6, 30), lines=[_line(amount_minor=1_125_000)]
                    ),
                    actor=ACTOR,
                )
                await session.commit()
                event = (await session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "catalog.rate.superseded"))).one()
                self.assertFalse(has_float(event.payload_json))
                self.assertIn("min_delta_bps", event.payload_json["diff"])

        asyncio.run(scenario())

    def test_rate_line_persistence_uses_kernel_amount_validation(self):
        with patch("services.rate_service.validate_amount_minor", return_value=123) as validate:
            values = RateService._line_values([_line(amount_minor=123)], actor=ACTOR)
        validate.assert_called_once_with(123)
        self.assertEqual(values[0]["amount_minor"], 123)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from schemas.v2.quote_request import QuoteRequestCreateSchema, QuoteRequestEditPayloadSchema
from services.quote_request_service import QuoteRequestService


class TestQuoteRequestRevisions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.db_file.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_file.name}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        if os.path.exists(self.db_file.name):
            os.unlink(self.db_file.name)

    async def test_create_and_edit_request_with_revisions(self):
        async with self.session_factory() as session:
            service = QuoteRequestService(session)

            # 1. Create Initial Request (Rev 1)
            create_payload = QuoteRequestCreateSchema(
                role="traveller",
                customer_name="Alice Smith",
                email="alice@example.com",
                phone="+1 555 1234",
                destinations=["Vietnam"],
                start_date="2026-10-01",
                end_date="2026-10-10",
                adults=2,
                children=0,
                travel_style="Living Heritage",
                budget=5000.0,
            )
            req = await service.create_quote_request(create_payload)
            await session.commit()

            self.assertIsNotNone(req.id)
            self.assertEqual(req.current_revision, 1)
            self.assertEqual(req.customer_name, "Alice Smith")
            self.assertEqual(req.adults, 2)

            req_id = req.id

        # Verify revision 1 exists
        async with self.session_factory() as session:
            service = QuoteRequestService(session)
            revisions = await service.get_request_revisions(req_id)
            self.assertEqual(len(revisions), 1)
            self.assertEqual(revisions[0].revision, 1)
            self.assertEqual(revisions[0].change_source, "initial_intake")
            self.assertEqual(revisions[0].customer_name, "Alice Smith")
            self.assertEqual(revisions[0].adults, 2)

        # 2. Edit Request (Rev 2): Increase to 4 adults, add child, change destinations
        async with self.session_factory() as session:
            service = QuoteRequestService(session)
            edit_payload = QuoteRequestEditPayloadSchema(
                role="traveller",
                customer_name="Alice & Bob Smith",
                email="alice@example.com",
                phone="+1 555 9999",
                destinations=["Vietnam", "Cambodia"],
                start_date="2026-11-01",
                end_date="2026-11-15",
                adults=4,
                children=1,
                kid_ages=[8],
                travel_style="Living Heritage",
                budget=10000.0,
                change_summary="Family members joined: increased adults to 4 and added 1 child",
            )
            updated_req, rev2 = await service.edit_quote_request(req_id, edit_payload)
            await session.commit()

            self.assertEqual(updated_req.current_revision, 2)
            self.assertEqual(updated_req.customer_name, "Alice & Bob Smith")
            self.assertEqual(updated_req.adults, 4)
            self.assertEqual(updated_req.children, 1)
            self.assertEqual(updated_req.destinations, ["Vietnam", "Cambodia"])
            self.assertEqual(rev2.revision, 2)
            self.assertEqual(rev2.change_summary, "Family members joined: increased adults to 4 and added 1 child")

        # 3. Verify Revisions History List (Descending Order)
        async with self.session_factory() as session:
            service = QuoteRequestService(session)
            revisions = await service.get_request_revisions(req_id)
            self.assertEqual(len(revisions), 2)
            self.assertEqual(revisions[0].revision, 2)
            self.assertEqual(revisions[1].revision, 1)

            # Verify Revision 1 snapshot is intact
            rev1 = await service.get_request_revision(req_id, 1)
            self.assertEqual(rev1.revision, 1)
            self.assertEqual(rev1.customer_name, "Alice Smith")
            self.assertEqual(rev1.adults, 2)
            self.assertEqual(rev1.children, 0)
            self.assertEqual(rev1.destinations, ["Vietnam"])

            # Verify Revision 2 snapshot is accurate
            rev2 = await service.get_request_revision(req_id, 2)
            self.assertEqual(rev2.revision, 2)
            self.assertEqual(rev2.customer_name, "Alice & Bob Smith")
            self.assertEqual(rev2.adults, 4)
            self.assertEqual(rev2.children, 1)
            self.assertEqual(rev2.destinations, ["Vietnam", "Cambodia"])

        # 4. Verify Pydantic Schema Validation with Expired Session (Regression Test for MissingGreenlet)
        async with self.session_factory() as session:
            service = QuoteRequestService(session)
            edit_payload = QuoteRequestEditPayloadSchema(
                role="traveller",
                customer_name="Alice, Bob & Charlie Smith",
                email="alice@example.com",
                phone="+1 555 9999",
                destinations=["Vietnam"],
                start_date="2026-11-01",
                end_date="2026-11-15",
                adults=3,
                children=0,
                travel_style="Living Heritage",
                budget=12000.0,
                change_summary="Updated guest count to 3 adults",
            )
            req3, rev3 = await service.edit_quote_request(req_id, edit_payload)
            await session.commit()
            await session.refresh(req3)

            from schemas.v2.quote_request import QuoteRequestResponseSchema
            validated = QuoteRequestResponseSchema.model_validate(req3)
            self.assertEqual(validated.current_revision, 3)
            self.assertEqual(validated.customer_name, "Alice, Bob & Charlie Smith")
            self.assertIsNotNone(validated.updated_at)

        # 5. Generate Quotation from latest revision (Rev 3)
        async with self.session_factory() as session:
            service = QuoteRequestService(session)
            gen_res = await service.generate_quotation_from_request(req_id)
            await session.commit()

            self.assertIn("quotation_id", gen_res)
            facts = gen_res["facts_snapshot"]
            # Must reflect latest state: 3 adults
            self.assertEqual(facts["customer_facts"]["adults"], 3)
            self.assertEqual(facts["trip_facts"]["destinations"], ["Vietnam"])

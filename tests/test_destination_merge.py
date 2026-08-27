import asyncio
import os
import tempfile
import unittest
import unittest.mock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models.destination import DestinationAlias, DestinationCatalog
from db.models.outbox import OutboxEvent
from db.models.product import Product
from repositories.destination_repository import DestinationMergeError, DestinationRepository


class DestinationMergeTests(unittest.TestCase):
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
            # dst_hub_a's canonical_name deliberately normalizes to a phrase that dst_hub_owner_c
            # already owns as an alias. Because normalized_alias is globally unique, A's own
            # upsert/create would have silently skipped claiming that phrase when A was created —
            # A never has its own alias row for it. That's the realistic collision merge() must
            # skip in step 2 (identity alias insertion), not the (impossible) repoint step.
            session.add(
                DestinationCatalog(id="dst_hub_a", canonical_name="Phrase Claimed Elsewhere", slug="old-hub-a")
            )
            session.add(DestinationCatalog(id="dst_hub_b", canonical_name="Hub B", slug="hub-b"))
            session.add(DestinationCatalog(id="dst_hub_inactive", canonical_name="Inactive Hub", slug="inactive-hub", is_active=False))
            session.add(DestinationCatalog(id="dst_hub_owner_c", canonical_name="Hub C Owner", slug="hub-c-owner"))

            session.add(DestinationAlias(id="dal_a_slug", destination_id="dst_hub_a", normalized_alias="old hub a"))
            session.add(DestinationAlias(id="dal_a_keyword", destination_id="dst_hub_a", normalized_alias="legacy name for a"))
            session.add(
                DestinationAlias(
                    id="dal_owner_c_phrase", destination_id="dst_hub_owner_c", normalized_alias="phrase claimed elsewhere"
                )
            )

            session.add(
                Product(
                    id="prd_in_hub_a",
                    destination_id="dst_hub_a",
                    category="ticket",
                    title="Old Hub A Ticket",
                    title_normalized="old hub a ticket",
                    unit="person",
                    time_basis="trip",
                )
            )
            await session.commit()

    def test_merge_is_atomic_and_repoints_aliases_skipping_collisions(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                merged = await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                self.assertEqual(merged.merged_into_id, "dst_hub_b")
                self.assertFalse(merged.is_active)

                target_aliases = (
                    await session.scalars(select(DestinationAlias).where(DestinationAlias.destination_id == "dst_hub_b"))
                ).all()
                target_alias_texts = {row.normalized_alias for row in target_aliases}
                self.assertIn("old hub a", target_alias_texts)
                self.assertIn("legacy name for a", target_alias_texts)

                # dst_hub_a's canonical_name collides with an alias dst_hub_owner_c already owns;
                # merge must skip claiming it for dst_hub_b rather than stealing it.
                collision_owner = await session.scalar(
                    select(DestinationAlias.destination_id).where(
                        DestinationAlias.normalized_alias == "phrase claimed elsewhere"
                    )
                )
                self.assertEqual(collision_owner, "dst_hub_owner_c")

        asyncio.run(scenario())

    def test_merge_marks_identity_aliases_for_the_ui_banner(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                identity_alias = await session.scalar(
                    select(DestinationAlias).where(DestinationAlias.normalized_alias == "old hub a")
                )
                self.assertTrue(identity_alias.is_merge_alias)
                self.assertEqual(identity_alias.source_slug, "old-hub-a")

                keyword_alias = await session.scalar(
                    select(DestinationAlias).where(DestinationAlias.normalized_alias == "legacy name for a")
                )
                self.assertFalse(keyword_alias.is_merge_alias)

        asyncio.run(scenario())

    def test_resolving_the_old_name_now_returns_the_target_hub(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                resolved = await repository.resolve("Old Hub A")
                self.assertIsNotNone(resolved)
                self.assertEqual(resolved.id, "dst_hub_b")

        asyncio.run(scenario())

    def test_search_excludes_merged_source_and_surfaces_target(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                rows = await repository.search("old hub a", active="true")
                ids = {row[0].id for row in rows}
                self.assertNotIn("dst_hub_a", ids)
                self.assertIn("dst_hub_b", ids)
                matched_row = next(row for row in rows if row[0].id == "dst_hub_b")
                self.assertTrue(matched_row[2])  # is_merge_alias
                self.assertEqual(matched_row[3], "old-hub-a")  # source_slug

        asyncio.run(scenario())

    def test_merge_does_not_repoint_product_foreign_keys(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                product = await session.get(Product, "prd_in_hub_a")
                self.assertEqual(product.destination_id, "dst_hub_a")

        asyncio.run(scenario())

    def test_effective_destination_id_resolves_old_products_to_the_live_hub(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                product = await session.get(Product, "prd_in_hub_a")
                live_id = await repository.effective_destination_id(product.destination_id)
                self.assertEqual(live_id, "dst_hub_b")

        asyncio.run(scenario())

    def test_cannot_merge_into_self(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                with self.assertRaises(DestinationMergeError):
                    await repository.merge(source_id="dst_hub_a", target_id="dst_hub_a")

        asyncio.run(scenario())

    def test_cannot_merge_into_inactive_target(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                with self.assertRaises(DestinationMergeError):
                    await repository.merge(source_id="dst_hub_a", target_id="dst_hub_inactive")

        asyncio.run(scenario())

    def test_cannot_merge_an_already_merged_source(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                with self.assertRaises(DestinationMergeError):
                    await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")

        asyncio.run(scenario())

    def test_cannot_merge_into_a_target_that_is_itself_merged(self):
        async def scenario():
            async with self.session_factory() as session:
                session.add(DestinationCatalog(id="dst_hub_d", canonical_name="Hub D", slug="hub-d"))
                await session.commit()

                repository = DestinationRepository(session)
                await repository.merge(source_id="dst_hub_a", target_id="dst_hub_b")
                await session.commit()

                with self.assertRaises(DestinationMergeError):
                    await repository.merge(source_id="dst_hub_d", target_id="dst_hub_a")

        asyncio.run(scenario())

    def test_merge_emits_outbox_event(self):
        async def scenario():
            import main

            async with self.session_factory() as session:
                with unittest.mock.patch.object(main, "_get_db_session_factory", return_value=self.session_factory):
                    await main._merge_destination(session, "dst_hub_a", "dst_hub_b", actor_email="ops@capella.test")
                    await session.commit()

                events = (
                    await session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "catalog.destination.merged"))
                ).all()
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].aggregate_id, "dst_hub_a")
                self.assertEqual(events[0].payload_json["targetId"], "dst_hub_b")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()

import asyncio
import os
import tempfile
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models.destination import DestinationCatalog
from repositories.destination_repository import DestinationHierarchyError, DestinationRepository


class DestinationHierarchyTests(unittest.TestCase):
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
            session.add(
                DestinationCatalog(
                    id="dst_country_vietnam", canonical_name="Vietnam", slug="country-vietnam", destination_type="country"
                )
            )
            session.add(
                DestinationCatalog(
                    id="dst_quang_ninh",
                    canonical_name="Quang Ninh",
                    slug="quang-ninh",
                    destination_type="province",
                    parent_id="dst_country_vietnam",
                )
            )
            session.add(
                DestinationCatalog(
                    id="dst_ha_long",
                    canonical_name="Ha Long",
                    slug="ha-long",
                    destination_type="city",
                    parent_id="dst_quang_ninh",
                )
            )
            session.add(
                DestinationCatalog(
                    id="dst_merged_away",
                    canonical_name="Old Hub",
                    slug="old-hub",
                    destination_type="city",
                    merged_into_id="dst_ha_long",
                    is_active=False,
                )
            )
            await session.commit()

    def test_valid_province_under_country_is_accepted(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.validate_parent(parent_id="dst_country_vietnam", destination_type="province")

        asyncio.run(scenario())

    def test_city_may_jump_straight_to_country(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.validate_parent(parent_id="dst_country_vietnam", destination_type="city")

        asyncio.run(scenario())

    def test_parent_must_outrank_child(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                with self.assertRaises(DestinationHierarchyError):
                    await repository.validate_parent(parent_id="dst_ha_long", destination_type="province")

        asyncio.run(scenario())

    def test_same_rank_parent_is_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                with self.assertRaises(DestinationHierarchyError):
                    await repository.validate_parent(parent_id="dst_quang_ninh", destination_type="province")

        asyncio.run(scenario())

    def test_self_parent_is_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                with self.assertRaises(DestinationHierarchyError):
                    await repository.validate_parent(
                        parent_id="dst_ha_long", destination_type="city", child_id="dst_ha_long"
                    )

        asyncio.run(scenario())

    def test_cycle_through_ancestor_chain_is_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                # dst_quang_ninh is an ancestor of dst_ha_long; making dst_ha_long the parent
                # of dst_quang_ninh (child_id) would create a cycle.
                with self.assertRaises(DestinationHierarchyError):
                    await repository.validate_parent(
                        parent_id="dst_ha_long", destination_type="country", child_id="dst_quang_ninh"
                    )

        asyncio.run(scenario())

    def test_merged_row_cannot_be_a_parent(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                with self.assertRaises(DestinationHierarchyError):
                    await repository.validate_parent(parent_id="dst_merged_away", destination_type="city")

        asyncio.run(scenario())

    def test_missing_parent_is_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                with self.assertRaises(DestinationHierarchyError):
                    await repository.validate_parent(parent_id="dst_does_not_exist", destination_type="city")

        asyncio.run(scenario())

    def test_none_parent_is_always_accepted(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                await repository.validate_parent(parent_id=None, destination_type="country")

        asyncio.run(scenario())

    def test_effective_destination_id_follows_merge_chain(self):
        async def scenario():
            async with self.session_factory() as session:
                repository = DestinationRepository(session)
                self.assertEqual(await repository.effective_destination_id("dst_merged_away"), "dst_ha_long")
                self.assertEqual(await repository.effective_destination_id("dst_ha_long"), "dst_ha_long")

        asyncio.run(scenario())

    def test_effective_destination_id_stops_at_max_depth(self):
        async def scenario():
            async with self.session_factory() as session:
                session.add(
                    DestinationCatalog(
                        id="dst_chain_a", canonical_name="A", slug="chain-a", merged_into_id="dst_chain_b", is_active=False
                    )
                )
                session.add(
                    DestinationCatalog(
                        id="dst_chain_b", canonical_name="B", slug="chain-b", merged_into_id="dst_chain_c", is_active=False
                    )
                )
                session.add(
                    DestinationCatalog(
                        id="dst_chain_c", canonical_name="C", slug="chain-c", merged_into_id="dst_chain_d", is_active=False
                    )
                )
                session.add(DestinationCatalog(id="dst_chain_d", canonical_name="D", slug="chain-d"))
                await session.commit()

                repository = DestinationRepository(session)
                # max_depth=2 means only 2 hops are followed from dst_chain_a.
                result = await repository.effective_destination_id("dst_chain_a", max_depth=2)
                self.assertEqual(result, "dst_chain_c")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()

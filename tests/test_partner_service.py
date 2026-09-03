import asyncio
import os
import tempfile
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from db.base import Base
from schemas.v2.partner import PartnerProfileCreateSchema, PartnerProfileUpdateSchema
from services.partner_service import PartnerService


class PartnerServiceTests(unittest.TestCase):
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

    def test_partner_lifecycle_and_commission(self):
        async def scenario():
            async with self.session_factory() as session:
                service = PartnerService(session)
                partner = await service.create_partner(
                    PartnerProfileCreateSchema(
                        company_name="Virtuoso London",
                        contact_name="Sarah Jenkins",
                        email="  Sarah@Virtuoso.co.uk ",
                        phone="+44 7700 900077",
                        market="United Kingdom",
                        tier="VIP",
                        default_commission_rate=12.5,
                        preferred_currency="GBP",
                    )
                )
                await session.commit()

                self.assertEqual(partner.email, "sarah@virtuoso.co.uk")
                self.assertEqual(partner.company_name, "Virtuoso London")
                self.assertEqual(partner.default_commission_rate, 12.5)
                self.assertEqual(partner.preferred_currency, "GBP")
                self.assertTrue(partner.is_active)

                # Search partners
                items, count = await service.list_partners(search="Virtuoso")
                self.assertEqual(count, 1)
                self.assertEqual(items[0].id, partner.id)

                # Update partner
                updated = await service.update_partner(
                    partner.id,
                    PartnerProfileUpdateSchema(
                        default_commission_rate=15.0,
                    ),
                )
                await session.commit()
                self.assertEqual(updated.default_commission_rate, 15.0)

                # Deactivate partner
                deactivated = await service.set_status(partner.id, is_active=False)
                await session.commit()
                self.assertFalse(deactivated.is_active)

                active_items, _ = await service.list_partners(active="true")
                self.assertEqual(len(active_items), 0)

                all_items, _ = await service.list_partners(active="all")
                self.assertEqual(len(all_items), 1)

        asyncio.run(scenario())

    def test_duplicate_email_rejected(self):
        async def scenario():
            async with self.session_factory() as session:
                service = PartnerService(session)
                await service.create_partner(
                    PartnerProfileCreateSchema(
                        company_name="Agency One",
                        contact_name="Contact One",
                        email="agency@example.com",
                    )
                )
                await session.commit()

                with self.assertRaises(ValueError):
                    await service.create_partner(
                        PartnerProfileCreateSchema(
                            company_name="Agency Two",
                            contact_name="Contact Two",
                            email="AGENCY@EXAMPLE.COM",
                        )
                    )

        asyncio.run(scenario())

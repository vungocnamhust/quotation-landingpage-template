from __future__ import annotations

import unittest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from notification.application.ingest_event import IngestEventUseCase
from notification.application.manage_inbox import MarkReadUseCase, QueryInboxUseCase
from notification.domain.events import EventType, IntegrationEvent, Severity
from notification.domain.models import Channel
from notification.domain.policy import NotificationPolicy
from notification.domain.templates import NotificationTemplateEngine
from notification.infrastructure.db.base import NotificationBase
from notification.infrastructure.db.repository import NotificationRepository


class TestNotificationDomainAndPolicy(unittest.TestCase):
    def test_policy_recipient_resolution(self):
        event = IntegrationEvent(
            event_id="evt_1",
            source_service="quotation-app",
            event_type=EventType.QUOTE_REQUEST_CREATED,
            aggregate_type="quote_request",
            aggregate_id="req_123",
            payload={
                "customer_name": "Nguyen Van A",
                "designer_email": "designer@dias.travel",
                "designer_profile_id": "prof_123",
            },
        )
        recipients = NotificationPolicy.resolve_recipients(event)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["email"], "designer@dias.travel")
        self.assertEqual(recipients[0]["profile_id"], "prof_123")

    def test_policy_actor_fallback(self):
        event = IntegrationEvent(
            event_id="evt_2",
            source_service="quotation-app",
            event_type=EventType.QUOTATION_CREATED,
            aggregate_type="quotation",
            aggregate_id="quo_999",
            actor_email="author@dias.travel",
            payload={"title": "Heritage Tour"},
        )
        recipients = NotificationPolicy.resolve_recipients(event)
        self.assertEqual(len(recipients), 1)
        self.assertEqual(recipients[0]["email"], "author@dias.travel")

    def test_policy_severity_and_action_url(self):
        event = IntegrationEvent(
            event_id="evt_3",
            source_service="quotation-app",
            event_type=EventType.QUOTATION_PDF_READY,
            aggregate_type="quotation",
            aggregate_id="quo_777",
            payload={"title": "Grand Indochina"},
        )
        severity = NotificationPolicy.resolve_severity(event)
        self.assertEqual(severity, Severity.SUCCESS)
        action_url = NotificationPolicy.resolve_action_url(event)
        self.assertEqual(action_url, "/workspace/quotations/quo_777?tab=pdf")

    def test_template_rendering(self):
        event_pub = IntegrationEvent(
            event_id="evt_4",
            source_service="quotation-app",
            event_type=EventType.QUOTATION_PUBLICATION_COMPLETED,
            aggregate_type="quotation",
            aggregate_id="quo_888",
            payload={"title": "Hanoi Luxury 5D4N"},
        )
        title, body = NotificationTemplateEngine.render(event_pub)
        self.assertEqual(title, "Quotation Published Successfully")
        self.assertIn("Hanoi Luxury 5D4N", body)

        event_agent = IntegrationEvent(
            event_id="evt_5",
            source_service="dmc-agentic-ai",
            event_type=EventType.AGENTIC_PLANNING_COMPLETED,
            aggregate_type="agentic_run",
            aggregate_id="run_101",
            payload={"run_title": "Multi-day Route Optimization"},
        )
        title_agent, body_agent = NotificationTemplateEngine.render(event_agent)
        self.assertEqual(title_agent, "Agentic Optimization Complete")
        self.assertIn("Multi-day Route Optimization", body_agent)


class TestNotificationRepositoryAndUseCases(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(NotificationBase.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_repository_deduplication_and_lifecycle(self):
        async with self.session_factory() as session:
            repo = NotificationRepository(session)

            # 1. Create notification
            n1 = await repo.create_notification(
                source_service="quotation-app",
                source_event_id="evt_dedupe_1",
                notification_type="quotation.pdf.ready",
                recipient_email="designer@dias.travel",
                title="PDF Ready",
                body="Your PDF is ready.",
                severity="success",
                action_url="/workspace/quotations/quo_1",
                channels=["INAPP_SSE", "EMAIL"],
            )
            await session.commit()
            self.assertIsNotNone(n1.id)

            # 2. Re-ingesting the exact same event returns the existing record (idempotency)
            n2 = await repo.create_notification(
                source_service="quotation-app",
                source_event_id="evt_dedupe_1",
                notification_type="quotation.pdf.ready",
                recipient_email="designer@dias.travel",
                title="PDF Ready",
                body="Your PDF is ready.",
                severity="success",
            )
            self.assertEqual(n1.id, n2.id)

            # 3. Check unread count
            unread = await repo.count_unread_for_recipient("designer@dias.travel")
            self.assertEqual(unread, 1)

            # 4. List notifications
            items, total = await repo.list_for_recipient("designer@dias.travel", is_read=False)
            self.assertEqual(total, 1)
            self.assertEqual(items[0].id, n1.id)

            # 5. Mark as read
            updated = await repo.mark_read(n1.id, "designer@dias.travel")
            await session.commit()
            self.assertIsNotNone(updated)
            self.assertTrue(updated.is_read)

            unread_after = await repo.count_unread_for_recipient("designer@dias.travel")
            self.assertEqual(unread_after, 0)

    async def test_ingest_event_use_case(self):
        async with self.session_factory() as session:
            use_case = IngestEventUseCase(session)
            event = IntegrationEvent(
                event_id="evt_ingest_99",
                source_service="dmc-agentic-ai",
                event_type=EventType.AGENTIC_COST_OPTIMIZATION_ALERT,
                aggregate_type="quotation",
                aggregate_id="quo_555",
                brand_id="selvara",
                payload={
                    "recipient_email": "agent.lead@dias.travel",
                    "margin_delta": "+5.2% margin improvement",
                },
            )
            created = await use_case.execute(event)
            self.assertEqual(len(created), 1)
            notif = created[0]
            self.assertEqual(notif.recipient_email, "agent.lead@dias.travel")
            self.assertEqual(notif.severity, "warning")
            self.assertEqual(notif.source_service, "dmc-agentic-ai")

            # Verify query inbox use case
            inbox_uc = QueryInboxUseCase(session)
            items, total, unread = await inbox_uc.list_notifications("agent.lead@dias.travel")
            self.assertEqual(total, 1)
            self.assertEqual(unread, 1)
            self.assertEqual(items[0].title, "Cost Optimization Notice")

            # Verify mark all as read
            mark_uc = MarkReadUseCase(session)
            marked, unread_remaining = await mark_uc.mark_all_read("agent.lead@dias.travel")
            self.assertEqual(marked, 1)
            self.assertEqual(unread_remaining, 0)
            self.assertEqual(await inbox_uc.get_unread_count("agent.lead@dias.travel"), 0)

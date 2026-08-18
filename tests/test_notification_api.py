from __future__ import annotations

import unittest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from notification.infrastructure.db.base import NotificationBase, get_notification_db
from notification.main import app
from notification.workers.delivery_worker import process_batch


class TestNotificationAPI(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(NotificationBase.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

        async def override_get_db():
            async with self.session_factory() as session:
                yield session

        self.override_get_db = override_get_db
        app.dependency_overrides[get_notification_db] = override_get_db
        self.client = TestClient(app)

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        from main import app as main_app
        main_app.dependency_overrides.clear()
        await self.engine.dispose()

    def test_health_check(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_end_to_end_notification_api_flow(self):
        headers = {
            "X-DMC-Email": "designer@dias.travel",
            "X-DMC-Role": "travel_designer",
        }

        # 1. Ingest Event
        event_payload = {
            "event_id": "evt_api_test_1",
            "source_service": "quotation-app",
            "event_type": "quotation.publication.completed",
            "aggregate_type": "quotation",
            "aggregate_id": "quo_api_123",
            "brand_id": "selvara",
            "payload": {
                "recipient_email": "designer@dias.travel",
                "title": "Vietnam Luxury 8D7N",
            },
        }
        resp = self.client.post("/api/v2/events", json=event_payload, headers=headers)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.json()["success"])
        self.assertEqual(resp.json()["notifications_created"], 1)

        # 2. Check Unread Count
        resp_count = self.client.get("/api/v2/notifications/unread-count", headers=headers)
        self.assertEqual(resp_count.status_code, 200)
        self.assertEqual(resp_count.json()["unread_count"], 1)

        # 3. List Notifications
        resp_list = self.client.get("/api/v2/notifications", headers=headers)
        self.assertEqual(resp_list.status_code, 200)
        data = resp_list.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["unread_count"], 1)
        notif_id = data["items"][0]["id"]
        self.assertEqual(data["items"][0]["title"], "Quotation Published Successfully")
        self.assertEqual(data["items"][0]["severity"], "success")

        # 4. Mark Single as Read
        resp_read = self.client.patch(f"/api/v2/notifications/{notif_id}/read", headers=headers)
        self.assertEqual(resp_read.status_code, 200)
        self.assertTrue(resp_read.json()["is_read"])

        # 5. Check Unread Count becomes 0
        resp_count2 = self.client.get("/api/v2/notifications/unread-count", headers=headers)
        self.assertEqual(resp_count2.json()["unread_count"], 0)

        # 6. Ingest another event & Mark All Read
        event_payload_2 = {
            "event_id": "evt_api_test_2",
            "source_service": "dmc-agentic-ai",
            "event_type": "agentic.planning.completed",
            "aggregate_type": "agentic_run",
            "aggregate_id": "run_456",
            "payload": {
                "recipient_email": "designer@dias.travel",
                "run_title": "Automated Pricing Run",
            },
        }
        self.client.post("/api/v2/events", json=event_payload_2, headers=headers)
        resp_mark_all = self.client.post("/api/v2/notifications/mark-all-read", headers=headers)
        self.assertEqual(resp_mark_all.status_code, 200)
        self.assertEqual(resp_mark_all.json()["marked_count"], 1)
        self.assertEqual(resp_mark_all.json()["unread_count"], 0)

    def test_mark_all_read_idempotency_and_isolation(self):
        user_a_headers = {"X-DMC-Email": "user_a@dias.travel"}
        user_b_headers = {"X-DMC-Email": "user_b@dias.travel"}

        # Ingest 3 events for User A and 2 events for User B
        for i in range(3):
            self.client.post("/api/v2/events", json={
                "event_id": f"evt_iso_a_{i}",
                "source_service": "quotation-app",
                "event_type": "quotation.publication.completed",
                "aggregate_type": "quotation",
                "aggregate_id": f"quo_a_{i}",
                "payload": {"recipient_email": "user_a@dias.travel", "title": f"Quote A {i}"},
            }, headers=user_a_headers)

        for j in range(2):
            self.client.post("/api/v2/events", json={
                "event_id": f"evt_iso_b_{j}",
                "source_service": "quotation-app",
                "event_type": "quotation.publication.completed",
                "aggregate_type": "quotation",
                "aggregate_id": f"quo_b_{j}",
                "payload": {"recipient_email": "user_b@dias.travel", "title": f"Quote B {j}"},
            }, headers=user_b_headers)

        # Verify initial unread counts
        resp_a = self.client.get("/api/v2/notifications/unread-count", headers=user_a_headers)
        self.assertEqual(resp_a.json()["unread_count"], 3)
        resp_b = self.client.get("/api/v2/notifications/unread-count", headers=user_b_headers)
        self.assertEqual(resp_b.json()["unread_count"], 2)

        # User A calls mark-all-read
        resp_mark_a = self.client.post("/api/v2/notifications/mark-all-read", headers=user_a_headers)
        self.assertEqual(resp_mark_a.status_code, 200)
        self.assertEqual(resp_mark_a.json()["marked_count"], 3)
        self.assertEqual(resp_mark_a.json()["unread_count"], 0)

        # User A calls mark-all-read a 2nd time (Idempotency)
        resp_mark_a_2 = self.client.post("/api/v2/notifications/mark-all-read", headers=user_a_headers)
        self.assertEqual(resp_mark_a_2.status_code, 200)
        self.assertEqual(resp_mark_a_2.json()["marked_count"], 0)
        self.assertEqual(resp_mark_a_2.json()["unread_count"], 0)

        # User B's unread notifications must remain completely untouched (Isolation)
        resp_b_after = self.client.get("/api/v2/notifications/unread-count", headers=user_b_headers)
        self.assertEqual(resp_b_after.json()["unread_count"], 2)

    def test_mark_all_read_via_main_quotation_app(self):
        from main import app as main_app
        main_app.dependency_overrides[get_notification_db] = self.override_get_db
        main_client = TestClient(main_app)
        headers = {"X-DMC-Email": "main_app_user@dias.travel"}

        # Ingest event via main app
        main_client.post("/api/v2/events", json={
            "event_id": "evt_main_app_1",
            "source_service": "quotation-app",
            "event_type": "quotation.publication.completed",
            "aggregate_type": "quotation",
            "aggregate_id": "quo_main_1",
            "payload": {"recipient_email": "main_app_user@dias.travel", "title": "Main App Quote"},
        }, headers=headers)

        # Mark all read via main app
        resp = main_client.post("/api/v2/notifications/mark-all-read", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["marked_count"], 1)
        self.assertEqual(resp.json()["unread_count"], 0)

    async def test_delivery_worker_processing(self):
        headers = {"X-DMC-Email": "worker.test@dias.travel"}
        self.client.post("/api/v2/events", json={
            "event_id": "evt_worker_1",
            "source_service": "quotation-app",
            "event_type": "quotation.pdf.ready",
            "aggregate_type": "quotation",
            "aggregate_id": "quo_w1",
            "payload": {"recipient_email": "worker.test@dias.travel", "title": "Worker Test Quote"},
        }, headers=headers)

        async with self.session_factory() as session:
            processed = await process_batch(session)
            self.assertGreaterEqual(processed, 1)

"""Fast Track progress broadcaster (Plan 16.3 F-21 — real SSE progress)."""
import asyncio
import unittest

from services.fast_track_progress import FastTrackProgressBroadcaster, ProgressEmitter


class FastTrackProgressBroadcasterTests(unittest.IsolatedAsyncioTestCase):
    async def test_subscriber_receives_published_event(self):
        broadcaster = FastTrackProgressBroadcaster()
        queue = await broadcaster.subscribe("corr-1")
        await broadcaster.publish("corr-1", {"event": "progress", "data": {"stage": "media"}})
        item = await asyncio.wait_for(queue.get(), timeout=1.0)
        self.assertEqual(item["data"]["stage"], "media")

    async def test_publish_to_unrelated_correlation_id_is_not_delivered(self):
        broadcaster = FastTrackProgressBroadcaster()
        queue = await broadcaster.subscribe("corr-a")
        await broadcaster.publish("corr-b", {"event": "progress", "data": {}})
        self.assertTrue(queue.empty())

    async def test_unsubscribe_stops_further_delivery(self):
        broadcaster = FastTrackProgressBroadcaster()
        queue = await broadcaster.subscribe("corr-1")
        await broadcaster.unsubscribe("corr-1", queue)
        await broadcaster.publish("corr-1", {"event": "progress", "data": {}})
        self.assertTrue(queue.empty())

    async def test_multiple_subscribers_on_same_correlation_id_both_receive(self):
        broadcaster = FastTrackProgressBroadcaster()
        queue_a = await broadcaster.subscribe("corr-1")
        queue_b = await broadcaster.subscribe("corr-1")
        await broadcaster.publish("corr-1", {"event": "progress", "data": {"stage": "review"}})
        item_a = await asyncio.wait_for(queue_a.get(), timeout=1.0)
        item_b = await asyncio.wait_for(queue_b.get(), timeout=1.0)
        self.assertEqual(item_a["data"]["stage"], "review")
        self.assertEqual(item_b["data"]["stage"], "review")


class ProgressEmitterTests(unittest.IsolatedAsyncioTestCase):
    async def test_emit_complete_and_error_publish_the_expected_event_names(self):
        broadcaster = FastTrackProgressBroadcaster()
        queue = await broadcaster.subscribe("corr-1")
        emitter = ProgressEmitter(correlation_id="corr-1", broadcaster=broadcaster)

        await emitter.emit(stage="media", message="Resolving media...", current=1, total=3)
        await emitter.complete(current_revision=9)
        await emitter.error(message="boom")

        first = await asyncio.wait_for(queue.get(), timeout=1.0)
        second = await asyncio.wait_for(queue.get(), timeout=1.0)
        third = await asyncio.wait_for(queue.get(), timeout=1.0)

        self.assertEqual(first["event"], "progress")
        self.assertEqual(first["data"], {"stage": "media", "message": "Resolving media...", "current": 1, "total": 3})
        self.assertEqual(second["event"], "complete")
        self.assertEqual(second["data"]["currentRevision"], 9)
        self.assertEqual(third["event"], "error")
        self.assertEqual(third["data"]["message"], "boom")


if __name__ == "__main__":
    unittest.main()

"""Fast Track assembly orchestration tests (Plan 16.3 CF3 — first backend coverage).

Unit-level: repositories and the content-action service are stubbed so these
tests pin orchestration semantics (replay-before-guard, typed 404, 409, and
all-or-nothing generation) without a full app stack.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from repositories.errors import DocumentRevisionConflictError
from services.fast_track_assembly_service import (
    FastTrackAssemblyService,
    FastTrackNotFoundError,
    FastTrackReviewBlockedError,
)


class FakeProgressEmitter:
    """Records emit()/complete()/error() calls in order (Plan 16.3 F-21)."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def emit(self, *, stage, message, current=None, total=None):
        self.events.append(("progress", {"stage": stage, "message": message, "current": current, "total": total}))

    async def complete(self, *, current_revision):
        self.events.append(("complete", {"currentRevision": current_revision}))

    async def error(self, *, message):
        self.events.append(("error", {"message": message}))


def _action(action_id: str, state: str, policy: str = "bypass") -> SimpleNamespace:
    return SimpleNamespace(id=action_id, state=state, automation_policy=policy)


def _service_with(quotation, document) -> FastTrackAssemblyService:
    service = FastTrackAssemblyService(MagicMock())
    service.quotations = MagicMock()
    service.quotations.get_quotation_by_id = AsyncMock(return_value=quotation)
    service.documents = MagicMock()
    service.documents.get_current_document = AsyncMock(return_value=document)
    return service


def _assemble_kwargs(**overrides):
    kwargs = dict(
        quotation_id="quo_1",
        lang="en",
        base_revision=1,
        writing_style="storytelling",
        profile_id=None,
        correlation_id="corr-1",
        idempotency_key="key-1",
        apply_media_defaults=AsyncMock(return_value={"hasChanges": False}),
        normalize_document=lambda document, revision: document,
        review_status=AsyncMock(return_value={"ready": True, "currentRevision": 7}),
    )
    kwargs.update(overrides)
    return kwargs


class FastTrackAssemblyTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_quotation_raises_typed_not_found(self):
        service = _service_with(None, None)
        with self.assertRaises(FastTrackNotFoundError):
            await service.assemble(**_assemble_kwargs())

    async def test_stale_base_revision_raises_document_conflict(self):
        document = SimpleNamespace(revision=5, document_json={"meta": {"revision": 5}})
        service = _service_with(SimpleNamespace(id="quo_1"), document)
        actions_service = MagicMock()
        actions_service.list = AsyncMock(return_value=(SimpleNamespace(id="cap_1"), [_action("act_1", "pending")]))
        with patch(
            "services.fast_track_assembly_service.ContentActionApplicationService",
            return_value=actions_service,
        ):
            with self.assertRaises(DocumentRevisionConflictError) as ctx:
                await service.assemble(**_assemble_kwargs(base_revision=1))
        self.assertEqual(ctx.exception.current_revision, 5)

    async def test_same_key_retry_replays_instead_of_409(self):
        """16.3 F-05/D4: after a committed assembly the revision has advanced —
        a same-key retry must return the original result, not a conflict."""
        document = SimpleNamespace(revision=5, document_json={"meta": {"revision": 5}})
        service = _service_with(SimpleNamespace(id="quo_1"), document)
        actions_service = MagicMock()
        actions_service.list = AsyncMock(
            return_value=(SimpleNamespace(id="cap_1"), [_action("act_1", "applied")])
        )
        actions_service.replay_bypass_if_idempotent = AsyncMock(return_value=([], 5))
        with patch(
            "services.fast_track_assembly_service.ContentActionApplicationService",
            return_value=actions_service,
        ):
            result = await service.assemble(**_assemble_kwargs(base_revision=1))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["currentRevision"], 7)
        actions_service.replay_bypass_if_idempotent.assert_awaited_once()

    async def test_different_key_retry_falls_through_to_conflict(self):
        document = SimpleNamespace(revision=5, document_json={"meta": {"revision": 5}})
        service = _service_with(SimpleNamespace(id="quo_1"), document)
        actions_service = MagicMock()
        actions_service.list = AsyncMock(
            return_value=(SimpleNamespace(id="cap_1"), [_action("act_1", "applied")])
        )
        actions_service.replay_bypass_if_idempotent = AsyncMock(return_value=None)
        with patch(
            "services.fast_track_assembly_service.ContentActionApplicationService",
            return_value=actions_service,
        ):
            with self.assertRaises(DocumentRevisionConflictError):
                await service.assemble(**_assemble_kwargs(base_revision=1))

    async def test_review_blocked_after_replay_surfaces_422_payload(self):
        document = SimpleNamespace(revision=5, document_json={"meta": {"revision": 5}})
        service = _service_with(SimpleNamespace(id="quo_1"), document)
        actions_service = MagicMock()
        actions_service.list = AsyncMock(
            return_value=(SimpleNamespace(id="cap_1"), [_action("act_1", "applied")])
        )
        actions_service.replay_bypass_if_idempotent = AsyncMock(return_value=([], 5))
        review = {"ready": False, "currentRevision": 5, "blockers": ["media"]}
        with patch(
            "services.fast_track_assembly_service.ContentActionApplicationService",
            return_value=actions_service,
        ):
            with self.assertRaises(FastTrackReviewBlockedError) as ctx:
                await service.assemble(
                    **_assemble_kwargs(base_revision=1, review_status=AsyncMock(return_value=review))
                )
        self.assertEqual(ctx.exception.review, review)

    async def test_replay_path_emits_real_progress_then_complete(self):
        """16.3 F-21: the replay fast-path must still narrate real stages, not fabricate counts."""
        document = SimpleNamespace(revision=5, document_json={"meta": {"revision": 5}})
        service = _service_with(SimpleNamespace(id="quo_1"), document)
        actions_service = MagicMock()
        actions_service.list = AsyncMock(
            return_value=(SimpleNamespace(id="cap_1"), [_action("act_1", "applied"), _action("act_2", "applied")])
        )
        actions_service.replay_bypass_if_idempotent = AsyncMock(return_value=([], 5))
        progress = FakeProgressEmitter()
        with patch(
            "services.fast_track_assembly_service.ContentActionApplicationService",
            return_value=actions_service,
        ):
            result = await service.assemble(**_assemble_kwargs(base_revision=1, progress=progress))

        self.assertEqual(result["status"], "complete")
        stages = [event for event, _ in progress.events]
        self.assertEqual(stages, ["progress", "complete"])
        replay_event = progress.events[0][1]
        self.assertEqual(replay_event["stage"], "content_generation")
        self.assertEqual(replay_event["current"], 2)
        self.assertEqual(replay_event["total"], 2)
        self.assertEqual(progress.events[1][1]["currentRevision"], 7)

    async def test_full_generation_path_reports_media_then_per_action_progress_then_complete(self):
        """16.3 F-21: real milestones — media, content_generation with per-action
        increments threaded from generate_and_apply, review, complete."""
        document = SimpleNamespace(revision=5, document_json={"meta": {"revision": 5}})
        service = _service_with(SimpleNamespace(id="quo_1"), document)
        actions_service = MagicMock()
        actions_service.list = AsyncMock(
            return_value=(SimpleNamespace(id="cap_1"), [_action("act_1", "pending"), _action("act_2", "pending")])
        )
        actions_service.accept = AsyncMock()

        async def _fake_generate_and_apply(**kwargs):
            on_action_complete = kwargs["on_action_complete"]
            await on_action_complete(1, 2)
            await on_action_complete(2, 2)
            return [], 6

        actions_service.generate_and_apply = AsyncMock(side_effect=_fake_generate_and_apply)
        progress = FakeProgressEmitter()
        with patch(
            "services.fast_track_assembly_service.ContentActionApplicationService",
            return_value=actions_service,
        ):
            result = await service.assemble(**_assemble_kwargs(base_revision=5, progress=progress))

        self.assertEqual(result["status"], "complete")
        stages = [(event, data.get("stage")) for event, data in progress.events]
        self.assertEqual(
            stages,
            [
                ("progress", "facts_media"),
                ("progress", "content_generation"),  # kickoff: current=0
                ("progress", "content_generation"),  # action 1/2 done
                ("progress", "content_generation"),  # action 2/2 done
                ("progress", "review"),
                ("complete", None),
            ],
        )
        kickoff, first_done, second_done = (progress.events[i][1] for i in (1, 2, 3))
        self.assertEqual((kickoff["current"], kickoff["total"]), (0, 2))
        self.assertEqual((first_done["current"], first_done["total"]), (1, 2))
        self.assertEqual((second_done["current"], second_done["total"]), (2, 2))


class GenerateAllConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_failed_generation_aborts_the_whole_batch(self):
        """All-or-nothing (16.3 F-07): the gather propagates the first failure."""
        from services.content_action_application_service import ContentActionApplicationService
        from services.section_content_generator import ContentGenerationError

        service = ContentActionApplicationService.__new__(ContentActionApplicationService)
        service.documents = MagicMock()
        service.drafts = MagicMock()
        service.quotes = MagicMock()
        service.quotes.get_version_facts = AsyncMock(
            return_value=SimpleNamespace(facts_hash="hash", canonical_facts_json={})
        )
        quotation = SimpleNamespace(id="quo_1", baseline_lang="en", parent_quotation_id=None, brand_id="brand_x")
        actions = [SimpleNamespace(id="act_1", scope="narrative"), SimpleNamespace(id="act_2", scope="route")]
        facts = MagicMock()
        facts.model_dump.return_value = {}

        async def _fake_generate(**kwargs):
            if kwargs["spec"].scope == "route":
                raise ContentGenerationError("Content generation did not return a valid draft. Please retry.")
            return {"narrative": {}}, {}

        with patch("services.content_action_application_service.SectionContentGenerator") as generator_cls, \
             patch("services.content_action_application_service.ContentDraftService") as draft_cls, \
             patch("services.content_action_application_service.InheritedContentContextService") as inherited_cls, \
             patch("services.content_action_application_service.scope_spec", side_effect=lambda scope: SimpleNamespace(scope=scope)), \
             patch("services.content_action_application_service._brand_generation_profile", return_value=MagicMock()):
            generator_cls.return_value.generate = AsyncMock(side_effect=_fake_generate)
            draft_service = draft_cls.return_value
            draft_service.facts_snapshot.return_value = {}
            draft_service.missing_for_scope.return_value = []
            draft_service.validate_candidate.side_effect = lambda scope, candidate: candidate
            inherited_cls.for_scope.return_value = {"status": "none", "hash": None}

            with self.assertRaises(ContentGenerationError):
                await service._generate_all(
                    actions=actions,
                    facts=facts,
                    document={"meta": {"revision": 1}},
                    quotation=quotation,
                    brand=MagicMock(),
                    writing_style="storytelling",
                )

    async def test_on_action_complete_fires_once_per_action_with_correct_totals(self):
        """16.3 F-21: real per-action progress survives the F-07 concurrency change."""
        from services.content_action_application_service import ContentActionApplicationService

        service = ContentActionApplicationService.__new__(ContentActionApplicationService)
        service.documents = MagicMock()
        service.drafts = MagicMock()
        service.quotes = MagicMock()
        service.quotes.get_version_facts = AsyncMock(
            return_value=SimpleNamespace(facts_hash="hash", canonical_facts_json={})
        )
        quotation = SimpleNamespace(id="quo_1", baseline_lang="en", parent_quotation_id=None, brand_id="brand_x")
        actions = [
            SimpleNamespace(id="act_1", scope="narrative"),
            SimpleNamespace(id="act_2", scope="route"),
            SimpleNamespace(id="act_3", scope="itinerary"),
        ]
        facts = MagicMock()
        facts.model_dump.return_value = {}
        reported: list[tuple[int, int]] = []

        async def _on_action_complete(done: int, total: int) -> None:
            reported.append((done, total))

        with patch("services.content_action_application_service.SectionContentGenerator") as generator_cls, \
             patch("services.content_action_application_service.ContentDraftService") as draft_cls, \
             patch("services.content_action_application_service.InheritedContentContextService") as inherited_cls, \
             patch("services.content_action_application_service.scope_spec", side_effect=lambda scope: SimpleNamespace(scope=scope)), \
             patch("services.content_action_application_service._brand_generation_profile", return_value=MagicMock()):
            generator_cls.return_value.generate = AsyncMock(return_value=({"narrative": {}}, {}))
            draft_service = draft_cls.return_value
            draft_service.facts_snapshot.return_value = {}
            draft_service.missing_for_scope.return_value = []
            draft_service.validate_candidate.side_effect = lambda scope, candidate: candidate
            inherited_cls.for_scope.return_value = {"status": "none", "hash": None}

            result = await service._generate_all(
                actions=actions,
                facts=facts,
                document={"meta": {"revision": 1}},
                quotation=quotation,
                brand=MagicMock(),
                writing_style="storytelling",
                on_action_complete=_on_action_complete,
            )

        self.assertEqual(len(result), 3)
        self.assertEqual(len(reported), 3)
        self.assertEqual({total for _, total in reported}, {3})
        self.assertEqual(sorted(done for done, _ in reported), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()

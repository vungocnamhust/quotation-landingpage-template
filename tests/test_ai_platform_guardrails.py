import pytest

from services.ai_platform.guardrails import (
    AllowlistRecorder,
    OutputValidator,
    RunBudget,
    RunBudgetExceededError,
)


class TestRunBudget:
    def test_records_calls_up_to_max(self):
        budget = RunBudget(max_calls=3)
        budget.record_call()
        budget.record_call()
        budget.record_call()
        assert budget.calls == 3

    def test_raises_once_exceeded(self):
        budget = RunBudget(max_calls=2)
        budget.record_call()
        budget.record_call()
        with pytest.raises(RunBudgetExceededError):
            budget.record_call()

    def test_stats_reports_calls_and_retries(self):
        budget = RunBudget(max_calls=5)
        budget.record_call()
        budget.record_retry()
        assert budget.stats() == {"calls": 1, "retries": 1, "tokens_in": 0, "tokens_out": 0}

    def test_record_usage_accumulates_tokens(self):
        budget = RunBudget(max_calls=5)

        class FakeUsage:
            input_tokens = 120
            output_tokens = 45

        budget.record_usage(FakeUsage())
        budget.record_usage(FakeUsage())
        assert budget.stats()["tokens_in"] == 240
        assert budget.stats()["tokens_out"] == 90

    def test_record_usage_tolerates_missing_attributes(self):
        budget = RunBudget(max_calls=5)
        budget.record_usage(object())
        assert budget.stats()["tokens_in"] == 0
        assert budget.stats()["tokens_out"] == 0


class TestAllowlistRecorder:
    def test_records_and_contains(self):
        allowlist = AllowlistRecorder()
        allowlist.record(["sup_abc", "sup_def", None])
        assert allowlist.contains("sup_abc")
        assert allowlist.contains("sup_def")

    def test_does_not_contain_unseen_id(self):
        allowlist = AllowlistRecorder()
        allowlist.record(["sup_abc"])
        assert not allowlist.contains("sup_invented")

    def test_contains_none_is_false(self):
        allowlist = AllowlistRecorder()
        assert not allowlist.contains(None)

    def test_snapshot_is_immutable(self):
        allowlist = AllowlistRecorder()
        allowlist.record(["sup_abc"])
        snapshot = allowlist.snapshot()
        assert snapshot == frozenset({"sup_abc"})
        with pytest.raises(AttributeError):
            snapshot.add("sup_new")  # frozenset has no .add


class TestOutputValidator:
    def test_filters_invalid_items_without_raising(self):
        validator = OutputValidator()
        items = [{"ok": True}, {"ok": False}, {"ok": True}]
        kept = validator.filter_valid(items, is_valid=lambda i: i["ok"], reason="missing field")
        assert kept == [{"ok": True}, {"ok": True}]
        assert validator.has_dropped()
        assert validator.dropped == [(1, "missing field")]

    def test_no_drops_when_all_valid(self):
        validator = OutputValidator()
        kept = validator.filter_valid([1, 2, 3], is_valid=lambda i: True, reason="n/a")
        assert kept == [1, 2, 3]
        assert not validator.has_dropped()

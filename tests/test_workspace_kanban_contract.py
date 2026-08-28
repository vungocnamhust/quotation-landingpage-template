import unittest

from services.workspace_service import classify_workflow_lane, commercial_summary, workflow_summary


class WorkspaceKanbanContractTests(unittest.TestCase):
    def test_lane_priority_is_published_then_first_incomplete_stage(self) -> None:
        ready = workflow_summary({
            "facts": {"ready": True},
            "content": {"ready": True},
            "design": {"ready": False},
            "review": {"ready": False},
        })
        self.assertEqual(classify_workflow_lane(status="draft", workflow=ready), "review")
        self.assertEqual(classify_workflow_lane(status="published", workflow=ready), "published")
        self.assertEqual(
            classify_workflow_lane(
                status="draft",
                workflow=workflow_summary({"facts": {"ready": False}}),
            ),
            "facts",
        )
        self.assertEqual(
            classify_workflow_lane(
                status="draft",
                workflow=workflow_summary({"facts": {"ready": True}, "content": {"ready": False}}),
            ),
            "content",
        )

    def test_commercial_summary_prefers_confirmed_main_option(self) -> None:
        summary = commercial_summary({"pricing": {"options": [
            {"label": "Alternative", "currency": "USD", "groupTotalAmountMinor": 10000, "isAlternativeOption": True},
            {"label": "Confirmed", "currency": "VND", "groupTotalAmountMinor": 2000000, "isConfirmedMainOption": True},
        ]}})
        self.assertEqual(summary, {"label": "Confirmed", "currency": "VND", "groupTotalAmountMinor": 2000000})


if __name__ == "__main__":
    unittest.main()

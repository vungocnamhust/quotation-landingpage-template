import unittest

import main


class V2ErrorEnvelopeTests(unittest.TestCase):
    def test_validation_envelope_preserves_legacy_detail_and_paths(self):
        detail = [{"loc": ["body", "customer_facts", "customer_name"], "msg": "Field required"}]
        payload = main._v2_error_payload(422, detail, request_id="request-1")

        self.assertEqual(payload["detail"], detail)
        self.assertEqual(payload["error"]["code"], "VALIDATION_FAILED")
        self.assertEqual(payload["error"]["fieldErrors"], [{"path": "customer_facts.customer_name", "message": "Field required"}])
        self.assertEqual(payload["error"]["requestId"], "request-1")

    def test_review_and_conflict_envelopes_keep_recovery_metadata(self):
        review = {"message": "Quotation is not ready to publish.", "review": {"ready": False}}
        blocked = main._v2_error_payload(422, review, request_id="request-2")
        conflict = main._v2_error_payload(409, {"message": "Document revision conflict.", "currentRevision": 7}, request_id="request-3")

        self.assertEqual(blocked["error"]["code"], "REVIEW_BLOCKED")
        self.assertEqual(blocked["error"]["recovery"], "open-blockers")
        self.assertEqual(conflict["error"]["code"], "REVISION_CONFLICT")
        self.assertEqual(conflict["error"]["currentRevision"], 7)
        self.assertEqual(conflict["error"]["recovery"], "reload")


if __name__ == "__main__":
    unittest.main()

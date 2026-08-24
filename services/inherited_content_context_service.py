"""Build bounded predecessor-reference context for Content generation."""
from __future__ import annotations

import copy
import json
from hashlib import sha256
from typing import Any

from core.rules.semantic_identity import itinerary_semantic_signature


class InheritedContentContextService:
    @staticmethod
    def for_scope(
        *,
        scope: str,
        predecessor_document: dict[str, Any] | None,
        predecessor_facts: dict[str, Any] | None,
        current_facts: dict[str, Any],
    ) -> dict[str, Any]:
        if not predecessor_document or not predecessor_facts:
            return {"status": "unavailable"}
        if not scope.startswith("itinerary:day:"):
            # Global predecessor prose can contain stale route/party/commercial
            # claims. Preserve no factual prose outside an eligible day scope.
            return {"status": "unavailable"}
        fact_id = scope.rsplit(":", 1)[-1]
        old_day = next((item for item in (predecessor_facts.get("trip_facts") or {}).get("itinerary") or [] if str(item.get("id")) == fact_id), None)
        new_day = next((item for item in (current_facts.get("trip_facts") or {}).get("itinerary") or [] if str(item.get("id")) == fact_id), None)
        if old_day is None:
            return {"status": "unavailable"}
        if new_day is None:
            return {"status": "retired"}
        if itinerary_semantic_signature(old_day) != itinerary_semantic_signature(new_day):
            return {"status": "unavailable"}
        old_document_day = next((item for item in ((predecessor_document.get("itinerary") or {}).get("days") or []) if str(item.get("sourceFactId")) == fact_id), None)
        if old_document_day is None:
            return {"status": "unavailable"}
        reference = {key: copy.deepcopy(old_document_day.get(key)) for key in ("title", "description", "activities")}
        digest = sha256(json.dumps(reference, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        return {"status": "eligible", "sourceQuotationId": predecessor_document.get("meta", {}).get("quotationId"), "content": reference, "hash": digest}

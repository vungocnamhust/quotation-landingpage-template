import pytest
from pydantic import ValidationError

from services.facts_contract import classify_facts_mutation, normalize_legacy_facts_snapshot
from quote_document import CreateQuoteRequestV1


def test_legacy_snapshot_drops_retired_editorial_trip_fields_and_normalizes_booking_html():
    source = {
        "trip_facts": {
            "destinations": ["Hanoi"],
            "title": "Retired AI title",
            "itinerary": [{"day_number": 1, "destination": "Hanoi", "display_title": "Retired title"}],
        },
        "booking_facts": {"items": [{"label": "Deposit", "body": "<p>Pay <strong>30%</strong> now; &lt; 20 days is non-refundable.</p>"}]},
    }

    normalized = normalize_legacy_facts_snapshot(source)

    assert "title" not in normalized["trip_facts"]
    assert "display_title" not in normalized["trip_facts"]["itinerary"][0]
    assert normalized["booking_facts"]["items"][0]["body"] == "Pay 30% now; less than 20 days is non-refundable."
    assert CreateQuoteRequestV1.model_validate(normalized).trip_facts.destinations == ["Hanoi"]
    assert source["booking_facts"]["items"][0]["body"].startswith("<p>")


@pytest.mark.parametrize("body", ["<ul><li>Deposit due.</li></ul>", "> 45 days prior", "< 20 days prior"])
def test_create_request_rejects_markup_and_angle_brackets_in_booking_fact_text(body):
    with pytest.raises(ValidationError, match="Booking/payment fact text must be plain text"):
        CreateQuoteRequestV1.model_validate(
            {"booking_facts": {"items": [{"label": "Deposit", "body": body}]}}
        )


def test_facts_mutation_policy_is_status_and_source_based_not_family_based():
    assert classify_facts_mutation("draft", "manual") == "mutable"
    assert classify_facts_mutation("published", "manual") == "revision_locked"
    assert classify_facts_mutation("draft", "imported") == "source_read_only"

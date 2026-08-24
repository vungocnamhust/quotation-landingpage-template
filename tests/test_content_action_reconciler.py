from core.rules.content_action_reconciler import content_input_fingerprint, reconcile_itinerary_entities
from core.rules.semantic_identity import assign_missing_source_fact_ids


def _day(identifier: str, number: int, destination: str, overnight: str | None = None) -> dict[str, object]:
    return {"id": identifier, "day_number": number, "destination": destination, "overnight": overnight or destination}


def test_assigns_missing_ids_once_without_replacing_existing_identity() -> None:
    assigned = assign_missing_source_fact_ids([{"id": "day_kept"}, {"destination": "Hanoi"}], creation_namespace="quo_test", kind="itinerary_day")
    assert assigned[0]["id"] == "day_kept"
    assert str(assigned[1]["id"]).startswith("itinerary_day_")


def test_hanoi_replacement_forbids_carry_forward_and_new_day_is_added() -> None:
    changes = reconcile_itinerary_entities(
        [_day("day_5", 5, "Hoi An")],
        [_day("day_5", 5, "Hanoi"), _day("day_6", 6, "Hanoi")],
    )
    by_key = {change.entity_key: change for change in changes}
    assert by_key["day:day_5"].operation == "semantic_replaced"
    assert not by_key["day:day_5"].carry_forward_allowed
    assert by_key["day:day_6"].operation == "added"


def test_reorder_preserves_identity_and_removal_retires_it() -> None:
    reordered = reconcile_itinerary_entities([_day("day_1", 1, "Hanoi")], [_day("day_1", 2, "Hanoi")])
    assert reordered[0].operation == "reordered"
    assert reordered[0].carry_forward_allowed
    removed = reconcile_itinerary_entities([_day("day_1", 1, "Hanoi")], [])
    assert removed[0].operation == "removed"
    assert not removed[0].carry_forward_allowed


def test_input_fingerprint_is_order_stable_for_object_keys() -> None:
    assert content_input_fingerprint({"a": 1, "b": [2]}) == content_input_fingerprint({"b": [2], "a": 1})

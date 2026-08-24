from core.rules.content_action_reconciler import content_input_fingerprint, reconcile_itinerary_entities
from core.rules.semantic_identity import assign_missing_source_fact_ids
from services.inherited_content_context_service import InheritedContentContextService
from services.quotation_change_plan_service import QuotationChangePlanService


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


def test_change_plan_targets_replaced_and_added_days_without_recreating_stable_days() -> None:
    previous = {
        "trip_facts": {"destinations": ["Hoi An"], "itinerary": [_day("day_5", 5, "Hoi An"), _day("day_4", 4, "Hue")]},
        "customer_facts": {}, "service_facts": {"hotels": []}, "pricing_facts": {},
    }
    current = {
        "trip_facts": {"destinations": ["Hanoi"], "itinerary": [_day("day_5", 5, "Hanoi"), _day("day_4", 4, "Hue"), _day("day_6", 6, "Hanoi")]},
        "customer_facts": {}, "service_facts": {"hotels": []}, "pricing_facts": {},
    }
    actions = QuotationChangePlanService.build(previous, current)
    day_actions = {action.entity_key: action for action in actions if action.scope.startswith("itinerary:day:")}
    assert day_actions["day:day_5"].reason_code == "semantic_replaced"
    assert day_actions["day:day_6"].reason_code == "added"
    assert "day:day_4" not in day_actions


def test_inherited_context_excludes_hoi_an_prose_after_hanoi_replacement() -> None:
    predecessor_facts = {"trip_facts": {"itinerary": [_day("day_5", 5, "Hoi An")]}}
    current_facts = {"trip_facts": {"itinerary": [_day("day_5", 5, "Hanoi")]}}
    predecessor_document = {"meta": {"quotationId": "quo_old"}, "itinerary": {"days": [{"sourceFactId": "day_5", "title": "Hoi An morning", "description": ["Hoi An prose"], "activities": []}]}}
    result = InheritedContentContextService.for_scope(scope="itinerary:day:day_5", predecessor_document=predecessor_document, predecessor_facts=predecessor_facts, current_facts=current_facts)
    assert result == {"status": "unavailable"}


def test_change_plan_persistence_uses_one_plan_and_action_rows() -> None:
    class Repository:
        def __init__(self):
            self.plan = None
            self.actions = None

        async def create_plan(self, **kwargs):
            self.plan = kwargs

        async def create_actions(self, **kwargs):
            self.actions = kwargs
            return kwargs["values"]

    import asyncio
    actions = QuotationChangePlanService.build(
        {"trip_facts": {"destinations": ["Hoi An"], "itinerary": [_day("day_5", 5, "Hoi An")]}, "customer_facts": {}, "service_facts": {"hotels": []}, "pricing_facts": {}},
        {"trip_facts": {"destinations": ["Hanoi"], "itinerary": [_day("day_5", 5, "Hanoi")]}, "customer_facts": {}, "service_facts": {"hotels": []}, "pricing_facts": {}},
    )
    repository = Repository()
    plan_id, rows = asyncio.run(QuotationChangePlanService.persist(repository=repository, quotation_id="quo_new", predecessor_quotation_id="quo_old", facts_hash="a" * 64, correlation_id="corr", actions=actions))
    assert plan_id.startswith("cap_")
    assert repository.plan["quotation_id"] == "quo_new"
    assert rows == repository.actions["values"]


def test_commercial_and_legal_fact_changes_create_manual_content_handoffs() -> None:
    previous = {"trip_facts": {"itinerary": []}, "customer_facts": {}, "service_facts": {"hotels": [], "inclusions": ["Guide"], "exclusions": ["Flights"]}, "pricing_facts": {"options": [{"id": "one", "label": "Private", "currency": "USD", "per_traveler_amount_minor": 100, "group_total_amount_minor": 200}], "conditions": []}}
    current = {"trip_facts": {"itinerary": []}, "customer_facts": {}, "service_facts": {"hotels": [{"id": "hotel_1", "name": "Hotel", "destination": "Hanoi"}], "inclusions": ["Guide", "Transfers"], "exclusions": ["Flights"]}, "pricing_facts": {"options": [{"id": "one", "label": "Private", "currency": "USD", "per_traveler_amount_minor": 120, "group_total_amount_minor": 240}], "conditions": []}}
    manual_scopes = {action.scope for action in QuotationChangePlanService.build(previous, current) if action.automation_policy == "manual"}
    assert {"hotel_plan", "pricing", "inclusions_exclusions"} <= manual_scopes

from services.quotation_impact_analysis import ImpactAnalysisService, facts_hash


def test_impact_analysis_is_deterministic_and_scoped() -> None:
    before = {
        "trip_facts": {"destinations": ["Hanoi"], "start_date": "2027-01-01", "end_date": "2027-01-04", "itinerary": [{"day_number": 1}]},
        "customer_facts": {"customer_name": "A"},
        "service_facts": {"hotels": [{"name": "One"}]},
        "pricing_facts": {"options": [{"label": "One"}]},
    }
    after = {**before, "trip_facts": {**before["trip_facts"], "destinations": ["Hanoi", "Hue"]}}

    impacts = ImpactAnalysisService.analyze(before, after)

    assert [(item["stage"], item["scope"]) for item in impacts] == [
        ("content", "hero"),
        ("content", "overview_letter"),
    ]
    assert facts_hash(before) == facts_hash(before)
    assert facts_hash(before) != facts_hash(after)


def test_impact_analysis_does_not_create_work_for_unchanged_facts() -> None:
    facts = {"trip_facts": {"destinations": ["Hanoi"], "itinerary": []}, "customer_facts": {}, "service_facts": {"hotels": []}, "pricing_facts": {}}
    assert ImpactAnalysisService.analyze(facts, facts) == []


def test_day_destination_change_and_added_day_have_concrete_targets() -> None:
    before = {"trip_facts": {"itinerary": [{"day_number": 5, "destination": "Hoi An", "overnight": "Hoi An"}]}, "customer_facts": {}, "pricing_facts": {"options": []}}
    after = {"trip_facts": {"itinerary": [{"day_number": 5, "destination": "Hanoi", "overnight": "Hanoi"}, {"day_number": 6, "destination": "Hanoi", "overnight": "Hanoi"}]}, "customer_facts": {}, "pricing_facts": {"options": []}}

    impacts = ImpactAnalysisService.analyze(before, after)

    by_scope = {(item["scope"], item["entity_key"]): item for item in impacts}
    assert by_scope[("itinerary:day:5", "day:5")]["generation_eligible"] is True
    assert by_scope[("itinerary:day:6", "day:6")]["operation"] == "added"
    assert by_scope[("itinerary:day:6", "day:6")]["targets"][0]["treatment"] == "generation_candidate"


def test_party_advisor_and_pricing_leaf_changes_are_mapped() -> None:
    before = {"trip_facts": {"itinerary": []}, "customer_facts": {"adults": 2, "advisor_name": "An"}, "pricing_facts": {"options": [{"id": "private", "label": "Private", "currency": "USD", "group_total_amount_minor": 100}]}}
    after = {"trip_facts": {"itinerary": []}, "customer_facts": {"adults": 3, "advisor_name": "Binh"}, "pricing_facts": {"options": [{"id": "private", "label": "Private", "currency": "EUR", "group_total_amount_minor": 100}]}}

    impacts = ImpactAnalysisService.analyze(before, after)

    assert any(item["source_path"] == "customer_facts.adults" and item["scope"] == "hero" for item in impacts)
    assert any(item["source_path"] == "customer_facts.advisor_name" and item["scope"] == "overview_letter" for item in impacts)
    assert not any(item["source_path"].startswith("pricing_facts") for item in impacts)


def test_reordered_stable_fact_days_do_not_invalidate_narrative() -> None:
    before = {"trip_facts": {"itinerary": [
        {"id": "fact-hanoi", "day_number": 1, "destination": "Hanoi"},
        {"id": "fact-hue", "day_number": 2, "destination": "Hue"},
    ]}, "customer_facts": {}, "pricing_facts": {"options": []}}
    after = {"trip_facts": {"itinerary": [
        {"id": "fact-hue", "day_number": 1, "destination": "Hue"},
        {"id": "fact-hanoi", "day_number": 2, "destination": "Hanoi"},
    ]}, "customer_facts": {}, "pricing_facts": {"options": []}}

    impacts = ImpactAnalysisService.analyze(before, after)

    assert not any(item["scope"].startswith("itinerary:day:") and item["generation_eligible"] for item in impacts)
    assert any(item["operation"] == "reordered" and item["entity_key"] == "day:fact-hue" for item in impacts)

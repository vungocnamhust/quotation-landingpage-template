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
        ("content", "route"),
        ("design", "route-map"),
    ]
    assert facts_hash(before) == facts_hash(before)
    assert facts_hash(before) != facts_hash(after)


def test_impact_analysis_does_not_create_work_for_unchanged_facts() -> None:
    facts = {"trip_facts": {"destinations": ["Hanoi"], "itinerary": []}, "customer_facts": {}, "service_facts": {"hotels": []}, "pricing_facts": {}}
    assert ImpactAnalysisService.analyze(facts, facts) == []

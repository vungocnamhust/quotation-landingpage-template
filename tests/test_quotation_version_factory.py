import asyncio

from quote_document import CreateQuoteRequestV1
from services.quotation_version_factory import CreateSuccessorCommand, QuotationVersionFactory


def _facts(destination: str) -> CreateQuoteRequestV1:
    return CreateQuoteRequestV1.model_validate({
        "trip_facts": {"itinerary": [{"day_number": 5, "destination": destination, "overnight": destination}]},
        "service_facts": {"hotels": [{"name": "Hotel", "destination": destination}]},
    })


def test_factory_assigns_ids_and_drops_incompatible_day_content() -> None:
    async def resolve(facts):
        return {"missingInputs": []}

    def build(facts, resolved):
        day = facts.trip_facts.itinerary[0]
        return {"itinerary": {"days": [{"sourceFactId": day.id, "segmentCity": day.destination, "overnight": day.overnight, "title": "", "description": [], "activities": []}]}, "presentation": {}}

    async def media(document, facts):
        return document

    factory = QuotationVersionFactory(resolve_facts=resolve, build_skeleton=build, resolve_media_defaults=media)
    predecessor = {"itinerary": {"days": [{"sourceFactId": "existing-day", "segmentCity": "Hoi An", "overnight": "Hoi An", "title": "Hoi An copy", "description": ["Old"], "activities": ["Old"]}]}, "presentation": {}}
    prepared = asyncio.run(factory.prepare(command=CreateSuccessorCommand("quo_parent", _facts("Hanoi"), 2, None, "corr"), predecessor_document=predecessor))
    assert prepared.facts.trip_facts.itinerary[0].id
    assert prepared.facts.service_facts.hotels[0].id
    assert prepared.document["itinerary"]["days"][0]["title"] == ""

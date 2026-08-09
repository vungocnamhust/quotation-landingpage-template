import unittest

from quote_document import CreateQuoteRequestV1
from services.facts_resolver import FactsResolutionError, FactsResolver


class Destination:
    id = "dst_ha-noi"
    canonical_name = "Hanoi"
    slug = "ha-noi"


async def resolve_destination(value: str):
    return Destination() if value.casefold().replace(" ", "-") == "ha-noi" else None


class FactsResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_alias_is_canonicalized_without_mutating_null_guest_facts(self):
        payload = CreateQuoteRequestV1.model_validate({
            "brand_id": "vietnam_safar", "lang": "en",
            "trip_facts": {"destinations": ["Ha Noi"], "itinerary": [{"day_number": 1, "destination": "Ha Noi", "summary": "Arrival."}]},
            "customer_facts": {"adults": None, "children": None},
        })
        canonical, resolved = await FactsResolver().resolve(payload, resolve_destination)
        self.assertEqual(canonical.trip_facts.destinations, ["Hanoi"])
        self.assertEqual(canonical.trip_facts.itinerary[0].destination, "Hanoi")
        self.assertIsNone(canonical.customer_facts.adults)
        self.assertEqual(resolved["routeDestinationRefs"][0]["id"], "dst_ha-noi")

    async def test_unknown_destination_is_atomic_error(self):
        payload = CreateQuoteRequestV1.model_validate({"brand_id": "vietnam_safar", "lang": "en", "trip_facts": {"destinations": ["Unknown"]}})
        with self.assertRaises(FactsResolutionError) as error:
            await FactsResolver().resolve(payload, resolve_destination)
        self.assertEqual(error.exception.missing_inputs, ["trip_facts.destinations[0]"])

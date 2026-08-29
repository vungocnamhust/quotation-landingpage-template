"""Plan 16.1 M2.2b — the write path uses the same {province} segment SSOT
the resolver's matcher assumes, resolved against real bucket data (M2.2a)."""
from db.models.destination import DestinationCatalog
from services.media_locations import accommodation_location, destination_location


def _destination(**overrides) -> DestinationCatalog:
    base = dict(
        id="dst_hanoi",
        canonical_name="Ha Noi",
        slug="ha-noi",
        country_slug="vietnam",
        region_slug="north",
        province_slug="ha-noi",
        is_active=True,
        media_prefix=None,
    )
    base.update(overrides)
    return DestinationCatalog(**base)


def test_destination_location_uses_the_hyphenated_province_slug_verbatim():
    location = destination_location(_destination())
    assert location.leaf_prefix == "vietnam/north/ha-noi/ha-noi"


def test_accommodation_location_prefix_matches_the_confirmed_bucket_grammar():
    location = accommodation_location(_destination(), "Metropole Hanoi", "hotel")
    assert location.leaf_prefix == "accommodations/vietnam/north/ha-noi/ha-noi/metropole-hanoi"

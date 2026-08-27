"""One-time baseline anchors and definitions for seeding the database destination catalogue.

The catalogue is authoritative after insert; this data serves as the Single Source of Truth
for bootstrapping destination anchors, geographic taxonomy, and rich keyword aliases.
"""
from __future__ import annotations

from typing import TypedDict
from core.rules.destination_rules import (
    COUNTRY_GATEWAY_MAP,
    DESTINATION_KEYWORD_MAP,
)

class DestinationSeedProfile(TypedDict, total=False):
    canonical_name: str
    slug: str
    country_slug: str
    region_slug: str
    province_slug: str
    latitude: float | None
    longitude: float | None
    aliases: list[str]
    parent_id: str | None
    timezone: str | None


# Known offset-preserving-but-distinct-identity timezone overrides (15.2b §6 step 3).
_TIMEZONE_OVERRIDES: dict[str, str] = {
    "bangkok": "Asia/Bangkok",
    "chiang-mai": "Asia/Bangkok",
    "phuket": "Asia/Bangkok",
}


class DestinationParentSeedProfile(TypedDict):
    """A Tourism Hub root (country-level) row (15.2b). Additive — city rows below hang off it
    via ``parent_id``; jumping straight from country to city is allowed by the hierarchy rules.
    """

    id: str
    canonical_name: str
    slug: str
    country_slug: str
    country_code: str
    destination_type: str
    latitude: float
    longitude: float
    timezone: str


# Country-level Tourism Hub roots. Centroids are the country's geographic/administrative
# centroid — deliberately coarse, since these rows only anchor the commercial tree and never
# gate an activation flow the way city-level coordinates do (15.2b §0 chốt 5).
COUNTRY_PARENT_PROFILES: list[DestinationParentSeedProfile] = [
    {
        "id": "dst_country_vietnam",
        "canonical_name": "Vietnam",
        "slug": "country-vietnam",
        "country_slug": "vietnam",
        "country_code": "VN",
        "destination_type": "country",
        "latitude": 14.0583,
        "longitude": 108.2772,
        "timezone": "Asia/Ho_Chi_Minh",
    },
    {
        "id": "dst_country_cambodia",
        "canonical_name": "Cambodia",
        "slug": "country-cambodia",
        "country_slug": "cambodia",
        "country_code": "KH",
        "destination_type": "country",
        "latitude": 12.5657,
        "longitude": 104.9910,
        "timezone": "Asia/Phnom_Penh",
    },
    {
        "id": "dst_country_laos",
        "canonical_name": "Laos",
        "slug": "country-laos",
        "country_slug": "laos",
        "country_code": "LA",
        "destination_type": "country",
        "latitude": 19.8563,
        "longitude": 102.4955,
        "timezone": "Asia/Vientiane",
    },
    {
        "id": "dst_country_thailand",
        "canonical_name": "Thailand",
        "slug": "country-thailand",
        "country_slug": "thailand",
        "country_code": "TH",
        "destination_type": "country",
        "latitude": 15.8700,
        "longitude": 100.9925,
        "timezone": "Asia/Bangkok",
    },
]


BASELINE_DESTINATION_COORDINATES: dict[str, tuple[float, float]] = {
    # Vietnam
    "ha-noi": (21.0285, 105.8542),
    "quang-ninh": (20.9599, 107.0436),
    "lao-cai": (22.3364, 103.8438),
    "da-nang": (16.0544, 108.2022),
    "quang-nam": (15.8801, 108.3380),
    "lam-dong": (11.9404, 108.4583),
    "ho-chi-minh": (10.8231, 106.6297),
    "khanh-hoa": (12.2388, 109.1967),
    "ninh-binh": (20.2539, 105.9750),
    "thua-thien-hue": (16.4637, 107.5909),
    "kien-giang": (10.2899, 103.9840),
    "binh-thuan": (10.9333, 108.1000),
    "can-tho": (10.0401, 105.7882),
    "mekong": (10.2435, 106.3756),
    "ha-giang": (22.8233, 104.9836),
    "nghe-an": (18.6736, 105.6811),
    "quang-binh": (17.4833, 106.6000),
    "hai-phong": (20.8449, 106.6881),
    "dak-lak": (12.6667, 108.0500),
    "gia-lai": (13.9833, 108.0000),
    "kon-tum": (14.3500, 108.0000),
    "ba-ria-vung-tau": (10.4114, 107.1363),
    "thanh-hoa": (19.8075, 105.7764),
    "phu-yen": (13.0881, 109.3025),
    "binh-dinh": (13.7753, 109.2294),
    "dien-bien": (21.3833, 103.0167),
    "son-la": (21.3333, 103.9167),
    "lai-chau": (22.4000, 103.4500),
    "yen-bai": (21.7000, 104.8667),
    "hoa-binh": (20.8167, 105.3333),
    "lang-son": (21.8500, 106.7500),
    "dong-nai": (10.9574, 106.8427),
    "binh-duong": (11.0000, 106.6667),
    "tien-giang": (10.3592, 106.3653),
    "dong-thap": (10.4500, 105.6333),
    "vinh-long": (10.2500, 105.9667),
    "an-giang": (10.3833, 105.4333),
    "cao-bang": (22.6667, 106.2500),
    # Cambodia
    "siem-reap": (13.3671, 103.8448),
    "phnom-penh": (11.5564, 104.9282),
    # Laos
    "luang-prabang": (19.8893, 102.1336),
    "vientiane": (17.9757, 102.6331),
    # Thailand
    "bangkok": (13.7563, 100.5018),
    "chiang-mai": (18.7883, 98.9853),
    "phuket": (7.8804, 98.3923),
}

# Base geographical profiles mapping (canonical name, country, region, province)
DESTINATION_BASE_PROFILES: dict[str, tuple[str, str, str, str]] = {
    # Vietnam
    "ha-noi": ("Hanoi", "vietnam", "north", "ha-noi"),
    "ninh-binh": ("Ninh Binh", "vietnam", "north", "ninh-binh"),
    "quang-ninh": ("Ha Long Bay", "vietnam", "north", "quang-ninh"),
    "lao-cai": ("Sapa", "vietnam", "north", "lao-cai"),
    "da-nang": ("Da Nang", "vietnam", "central", "da-nang"),
    "quang-nam": ("Hoi An", "vietnam", "central", "quang-nam"),
    "thua-thien-hue": ("Hue", "vietnam", "central", "thua-thien-hue"),
    "khanh-hoa": ("Nha Trang", "vietnam", "central", "khanh-hoa"),
    "lam-dong": ("Da Lat", "vietnam", "central-highlands", "lam-dong"),
    "ho-chi-minh": ("Ho Chi Minh City", "vietnam", "south", "ho-chi-minh"),
    "mekong": ("Mekong Delta", "vietnam", "south", "mekong"),
    "can-tho": ("Can Tho", "vietnam", "south", "can-tho"),
    "kien-giang": ("Phu Quoc", "vietnam", "south", "kien-giang"),
    "binh-thuan": ("Mui Ne", "vietnam", "central", "binh-thuan"),
    "quang-binh": ("Phong Nha", "vietnam", "north-central", "quang-binh"),
    "ha-giang": ("Ha Giang", "vietnam", "north", "ha-giang"),
    "cao-bang": ("Cao Bang", "vietnam", "north", "cao-bang"),
    "yen-bai": ("Mu Cang Chai", "vietnam", "north", "yen-bai"),
    "hai-phong": ("Hai Phong", "vietnam", "north", "hai-phong"),
    "binh-dinh": ("Quy Nhon", "vietnam", "central", "binh-dinh"),
    "phu-yen": ("Phu Yen", "vietnam", "central", "phu-yen"),
    "dak-lak": ("Buon Ma Thuot", "vietnam", "central-highlands", "dak-lak"),
    "ba-ria-vung-tau": ("Vung Tau", "vietnam", "south", "ba-ria-vung-tau"),
    # Cambodia
    "siem-reap": ("Siem Reap", "cambodia", "northwest", "siem-reap"),
    "phnom-penh": ("Phnom Penh", "cambodia", "central", "phnom-penh"),
    # Laos
    "luang-prabang": ("Luang Prabang", "laos", "north", "luang-prabang"),
    "vientiane": ("Vientiane", "laos", "central", "vientiane"),
    # Thailand
    "bangkok": ("Bangkok", "thailand", "central", "bangkok"),
    "chiang-mai": ("Chiang Mai", "thailand", "north", "chiang-mai"),
    "phuket": ("Phuket", "thailand", "south", "phuket"),
}


def get_seed_destination_profiles() -> list[DestinationSeedProfile]:
    """Build the comprehensive list of destination seed profiles with rich keyword aliases."""
    # Group keywords from DESTINATION_KEYWORD_MAP by target slug
    slug_to_keywords: dict[str, set[str]] = {}
    for keyword, slug in DESTINATION_KEYWORD_MAP.items():
        slug_to_keywords.setdefault(slug, set()).add(keyword)

    # Invert country gateways to append country names to primary gateway destinations
    gateway_slug_to_countries: dict[str, set[str]] = {}
    for country_name, gateway_slug in COUNTRY_GATEWAY_MAP.items():
        gateway_slug_to_countries.setdefault(gateway_slug, set()).add(country_name)

    profiles: list[DestinationSeedProfile] = []

    for slug, (canonical_name, country, region, province) in DESTINATION_BASE_PROFILES.items():
        coords = BASELINE_DESTINATION_COORDINATES.get(slug)
        aliases_set: set[str] = {
            canonical_name,
            slug,
            slug.replace("-", " "),
            province,
            province.replace("-", " "),
        }

        # Add all domain keywords mapped to this slug or province
        if slug in slug_to_keywords:
            aliases_set.update(slug_to_keywords[slug])
        if province in slug_to_keywords:
            aliases_set.update(slug_to_keywords[province])

        # Add country gateway aliases if this slug is the primary gateway
        if slug in gateway_slug_to_countries:
            aliases_set.update(gateway_slug_to_countries[slug])

        profiles.append(
            DestinationSeedProfile(
                canonical_name=canonical_name,
                slug=slug,
                country_slug=country,
                region_slug=region,
                province_slug=province,
                latitude=coords[0] if coords else None,
                longitude=coords[1] if coords else None,
                aliases=sorted(list(aliases_set)),
                parent_id=get_country_parent_id(country),
                timezone=_TIMEZONE_OVERRIDES.get(slug),
            )
        )

    return profiles


def get_country_parent_id(country_slug: str) -> str | None:
    """Tourism Hub root id for a given ``country_slug``, or None if there is no seeded root."""
    return next(
        (profile["id"] for profile in COUNTRY_PARENT_PROFILES if profile["country_slug"] == country_slug),
        None,
    )

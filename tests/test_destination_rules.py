import unittest

from core.rules.destination_rules import (
    COUNTRY_GATEWAY_MAP,
    DESTINATION_KEYWORD_MAP,
    VALID_DESTINATION_SLUGS,
    match_destination_slug,
    normalize_destination_text,
)
from destination_catalog_seed import get_seed_destination_profiles


class TestDestinationRules(unittest.TestCase):
    def test_normalize_destination_text(self):
        self.assertEqual(normalize_destination_text("  Ha-Noi  "), "ha noi")
        self.assertEqual(normalize_destination_text("Quang-Ninh"), "quang ninh")
        self.assertEqual(normalize_destination_text(""), "")
        self.assertEqual(normalize_destination_text(None), "")

    def test_direct_valid_slugs(self):
        self.assertEqual(match_destination_slug("ha-noi"), "ha-noi")
        self.assertEqual(match_destination_slug("quang-ninh"), "quang-ninh")
        self.assertEqual(match_destination_slug("siem-reap"), "siem-reap")
        self.assertEqual(match_destination_slug("luang-prabang"), "luang-prabang")
        self.assertEqual(match_destination_slug("bangkok"), "bangkok")

    def test_tourist_landmarks_and_english_variations(self):
        # Ha Long Bay variations
        self.assertEqual(match_destination_slug("Halong Bay"), "quang-ninh")
        self.assertEqual(match_destination_slug("Ha Long"), "quang-ninh")
        self.assertEqual(match_destination_slug("halong"), "quang-ninh")
        self.assertEqual(match_destination_slug("Vịnh Hạ Long"), "quang-ninh")
        self.assertEqual(match_destination_slug("Lan Ha Bay"), "quang-ninh")

        # Hoi An variations
        self.assertEqual(match_destination_slug("Hoi An"), "quang-nam")
        self.assertEqual(match_destination_slug("Hoi An Ancient Town"), "quang-nam")
        self.assertEqual(match_destination_slug("Phố cổ Hội An"), "quang-nam")
        self.assertEqual(match_destination_slug("hoian"), "quang-nam")

        # Sapa variations
        self.assertEqual(match_destination_slug("Sapa"), "lao-cai")
        self.assertEqual(match_destination_slug("Sa Pa"), "lao-cai")
        self.assertEqual(match_destination_slug("Fansipan"), "lao-cai")

        # Saigon / HCMC variations
        self.assertEqual(match_destination_slug("Saigon"), "ho-chi-minh")
        self.assertEqual(match_destination_slug("Sài Gòn"), "ho-chi-minh")
        self.assertEqual(match_destination_slug("HCMC"), "ho-chi-minh")
        self.assertEqual(match_destination_slug("Ho Chi Minh City"), "ho-chi-minh")
        self.assertEqual(match_destination_slug("TP.HCM"), "ho-chi-minh")

        # Mekong variations
        self.assertEqual(match_destination_slug("Mekong Delta"), "mekong")
        self.assertEqual(match_destination_slug("Đồng bằng sông Cửu Long"), "mekong")
        self.assertEqual(match_destination_slug("Miền Tây"), "mekong")

        # Ninh Binh / Trang An / Hue / Da Nang / Nha Trang
        self.assertEqual(match_destination_slug("Tràng An"), "ninh-binh")
        self.assertEqual(match_destination_slug("Tam Cốc"), "ninh-binh")
        self.assertEqual(match_destination_slug("Huế"), "thua-thien-hue")
        self.assertEqual(match_destination_slug("Cố đô Huế"), "thua-thien-hue")
        self.assertEqual(match_destination_slug("Đà Nẵng"), "da-nang")
        self.assertEqual(match_destination_slug("Bà Nà Hills"), "da-nang")
        self.assertEqual(match_destination_slug("Nha Trang"), "khanh-hoa")
        self.assertEqual(match_destination_slug("Cam Ranh"), "khanh-hoa")
        self.assertEqual(match_destination_slug("Đà Lạt"), "lam-dong")
        self.assertEqual(match_destination_slug("Phú Quốc"), "kien-giang")

        # Indochina & SE Asia landmarks
        self.assertEqual(match_destination_slug("Angkor Wat"), "siem-reap")
        self.assertEqual(match_destination_slug("Siem Reap"), "siem-reap")
        self.assertEqual(match_destination_slug("Phnom Penh"), "phnom-penh")
        self.assertEqual(match_destination_slug("Luang Prabang"), "luang-prabang")
        self.assertEqual(match_destination_slug("Chiang Mai"), "chiang-mai")
        self.assertEqual(match_destination_slug("Phuket"), "phuket")

    def test_country_gateway_resolution(self):
        self.assertEqual(match_destination_slug("Vietnam"), "ha-noi")
        self.assertEqual(match_destination_slug("Việt Nam"), "ha-noi")
        self.assertEqual(match_destination_slug("Cambodia"), "siem-reap")
        self.assertEqual(match_destination_slug("Campuchia"), "siem-reap")
        self.assertEqual(match_destination_slug("Laos"), "luang-prabang")
        self.assertEqual(match_destination_slug("Lào"), "luang-prabang")
        self.assertEqual(match_destination_slug("Thailand"), "bangkok")
        self.assertEqual(match_destination_slug("Thái Lan"), "bangkok")

    def test_substring_and_phrases(self):
        self.assertEqual(match_destination_slug("Luxury Cruise in Halong Bay"), "quang-ninh")
        self.assertEqual(match_destination_slug("Walking tour of Hoi An Ancient Town"), "quang-nam")
        self.assertEqual(match_destination_slug("Trip to Vietnam and beyond"), "ha-noi")

    def test_invalid_destination(self):
        self.assertIsNone(match_destination_slug("Antarctica Ice Cave"))
        self.assertIsNone(match_destination_slug(""))
        self.assertIsNone(match_destination_slug(None))

    def test_seed_profiles_completeness(self):
        profiles = get_seed_destination_profiles()
        self.assertGreater(len(profiles), 20)
        hanoi_profile = next((p for p in profiles if p["slug"] == "ha-noi"), None)
        self.assertIsNotNone(hanoi_profile)
        self.assertIn("vietnam", [a.lower() for a in hanoi_profile["aliases"]])
        self.assertIn("thudo", [a.lower() for a in hanoi_profile["aliases"]])

        halong_profile = next((p for p in profiles if p["slug"] == "quang-ninh"), None)
        self.assertIsNotNone(halong_profile)
        self.assertIn("halong bay", [a.lower() for a in halong_profile["aliases"]])
        self.assertIn("lan ha bay", [a.lower() for a in halong_profile["aliases"]])


if __name__ == "__main__":
    unittest.main()

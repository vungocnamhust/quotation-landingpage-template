"""Pure domain rules for destination keyword mapping, country gateways, and deterministic slug matching.

This module contains zero network calls, zero database dependencies, and zero LLM calls.
It serves as the Single Source of Truth for destination text matching and catalog aliases.
"""
from __future__ import annotations

# Supported destination slugs (Vietnam provinces + Indochina / SE Asia gateways)
VALID_DESTINATION_SLUGS: set[str] = {
    # Vietnam
    "an-giang", "ba-ria-vung-tau", "bac-lieu", "bac-kan", "bac-giang", "bac-ninh", "ben-tre",
    "binh-duong", "binh-dinh", "binh-phuoc", "binh-thuan", "ca-mau", "cao-bang", "can-tho",
    "da-nang", "dak-lak", "dak-nong", "dien-bien", "dong-nai", "dong-thap", "gia-lai",
    "ha-giang", "ha-nam", "ha-noi", "ha-tinh", "hai-duong", "hai-phong", "hau-giang",
    "hoa-binh", "hung-yen", "khanh-hoa", "kien-giang", "kon-tum", "lai-chau", "lang-son",
    "lao-cai", "lam-dong", "long-an", "mekong", "nam-dinh", "nghe-an", "ninh-binh", "ninh-thuan",
    "phu-tho", "phu-yen", "quang-binh", "quang-nam", "quang-ngai", "quang-ninh", "quang-tri",
    "soc-trang", "son-la", "tay-ninh", "thai-binh", "thai-nguyen", "thanh-hoa", "thua-thien-hue",
    "tien-giang", "ho-chi-minh", "tra-vinh", "tuyen-quang", "vinh-long", "vinh-phuc", "yen-bai",
    # Cambodia
    "siem-reap", "phnom-penh",
    # Laos
    "luang-prabang", "vientiane",
    # Thailand
    "bangkok", "chiang-mai", "phuket",
}

# Country to Primary Gateway slug mapping (used when customer submits country-level inquiry)
COUNTRY_GATEWAY_MAP: dict[str, str] = {
    "vietnam": "ha-noi",
    "việt nam": "ha-noi",
    "viet nam": "ha-noi",
    "cambodia": "siem-reap",
    "campuchia": "siem-reap",
    "laos": "luang-prabang",
    "lào": "luang-prabang",
    "thailand": "bangkok",
    "thái lan": "bangkok",
    "thai lan": "bangkok",
}

# Comprehensive dictionary mapping local landmarks, city names, diacritics, and aliases to destination slug
DESTINATION_KEYWORD_MAP: dict[str, str] = {
    # ── Vietnam: Northern Gateways & Landmarks ─────────────────────────────────
    "hà nội": "ha-noi", "ha noi": "ha-noi", "hanoi": "ha-noi", "hanoï": "ha-noi",
    "thủ đô": "ha-noi", "thu do": "ha-noi", "thudo": "ha-noi",

    "quảng ninh": "quang-ninh", "quang ninh": "quang-ninh",
    "hạ long": "quang-ninh", "ha long": "quang-ninh", "halong": "quang-ninh",
    "halong bay": "quang-ninh", "ha long bay": "quang-ninh",
    "vịnh hạ long": "quang-ninh", "vinh ha long": "quang-ninh",
    "lan hạ": "quang-ninh", "lan ha": "quang-ninh", "lan ha bay": "quang-ninh",
    "cát bà": "quang-ninh", "cat ba": "quang-ninh", "bái tử long": "quang-ninh", "bai tu long": "quang-ninh",

    "lào cai": "lao-cai", "lao cai": "lao-cai", "laocai": "lao-cai",
    "sapa": "lao-cai", "sa pa": "lao-cai", "fansipan": "lao-cai", "phan-xi-păng": "lao-cai",
    "bắc hà": "lao-cai", "bac ha": "lao-cai",

    "ninh bình": "ninh-binh", "ninh binh": "ninh-binh",
    "tràng an": "ninh-binh", "trang an": "ninh-binh",
    "tam cốc": "ninh-binh", "tam coc": "ninh-binh",
    "bích động": "ninh-binh", "bich dong": "ninh-binh",
    "hang múa": "ninh-binh", "hang mua": "ninh-binh",

    "hà giang": "ha-giang", "ha giang": "ha-giang",
    "đồng văn": "ha-giang", "dong van": "ha-giang",
    "mèo vạc": "ha-giang", "meo vac": "ha-giang",
    "mã pí lèng": "ha-giang", "ma pi leng": "ha-giang",

    "cao bằng": "cao-bang", "cao bang": "cao-bang",
    "bản giốc": "cao-bang", "ban gioc": "cao-bang", "ban gioc waterfall": "cao-bang",

    "yên bái": "yen-bai", "yen bai": "yen-bai",
    "mù cang chải": "yen-bai", "mu cang chai": "yen-bai",

    "hải phòng": "hai-phong", "hai phong": "hai-phong", "haiphong": "hai-phong",
    "điện biên": "dien-bien", "dien bien": "dien-bien", "điện biên phủ": "dien-bien",
    "sơn la": "son-la", "son la": "son-la", "mộc châu": "son-la", "moc chau": "son-la",
    "lai châu": "lai-chau", "lai chau": "lai-chau",
    "hoà bình": "hoa-binh", "hoa binh": "hoa-binh", "mai châu": "hoa-binh", "mai chau": "hoa-binh",
    "lạng sơn": "lang-son", "lang son": "lang-son",
    "bắc kạn": "bac-kan", "bac kan": "bac-kan", "ba bể": "bac-kan", "ba be": "bac-kan",

    # ── Vietnam: Central Region & Coast ───────────────────────────────────────
    "đà nẵng": "da-nang", "da nang": "da-nang", "danang": "da-nang",
    "bà nà": "da-nang", "ba na": "da-nang", "ba na hills": "da-nang",

    "quảng nam": "quang-nam", "quang nam": "quang-nam",
    "hội an": "quang-nam", "hoi an": "quang-nam", "hoian": "quang-nam",
    "phố cổ hội an": "quang-nam", "hoi an ancient town": "quang-nam",
    "mỹ sơn": "quang-nam", "my son": "quang-nam", "cù lao chàm": "quang-nam", "cu lao cham": "quang-nam",

    "thừa thiên huế": "thua-thien-hue", "thua thien hue": "thua-thien-hue",
    "huế": "thua-thien-hue", "hue": "thua-thien-hue", "cố đô huế": "thua-thien-hue",
    "lăng cô": "thua-thien-hue", "lang co": "thua-thien-hue",

    "quảng bình": "quang-binh", "quang binh": "quang-binh",
    "phong nha": "quang-binh", "kẻ bàng": "quang-binh", "ke bang": "quang-binh",
    "sơn đoòng": "quang-binh", "son doong": "quang-binh",

    "nghệ an": "nghe-an", "nghe an": "nghe-an", "cửa lò": "nghe-an", "cua lo": "nghe-an",
    "thanh hoá": "thanh-hoa", "thanh hoa": "thanh-hoa", "sầm sơn": "thanh-hoa", "sam son": "thanh-hoa",
    "quảng trị": "quang-tri", "quang tri": "quang-tri",
    "quảng ngãi": "quang-ngai", "quang ngai": "quang-ngai", "lý sơn": "quang-ngai", "ly son": "quang-ngai",

    "bình định": "binh-dinh", "binh dinh": "binh-dinh",
    "quy nhơn": "binh-dinh", "quy nhon": "binh-dinh", "quynhon": "binh-dinh",

    "phú yên": "phu-yen", "phu yen": "phu-yen", "tuy hoà": "phu-yen", "tuy hoa": "phu-yen",

    "khánh hoà": "khanh-hoa", "khanh hoa": "khanh-hoa",
    "nha trang": "khanh-hoa", "nhatrang": "khanh-hoa", "cam ranh": "khanh-hoa",

    "ninh thuận": "ninh-thuan", "ninh thuan": "ninh-thuan",
    "phan rang": "ninh-thuan", "vĩnh hy": "ninh-thuan", "vinh hy": "ninh-thuan",

    "bình thuận": "binh-thuan", "binh thuan": "binh-thuan",
    "mũi né": "binh-thuan", "mui ne": "binh-thuan", "muine": "binh-thuan",
    "phan thiết": "binh-thuan", "phan thiet": "binh-thuan",

    # ── Vietnam: Central Highlands ────────────────────────────────────────────
    "lâm đồng": "lam-dong", "lam dong": "lam-dong",
    "đà lạt": "lam-dong", "da lat": "lam-dong", "dalat": "lam-dong",

    "đắk lắk": "dak-lak", "dak lak": "dak-lak", "daklak": "dak-lak",
    "buôn ma thuột": "dak-lak", "buon ma thuot": "dak-lak", "bmt": "dak-lak",

    "gia lai": "gia-lai", "pleiku": "gia-lai",
    "kon tum": "kon-tum", "kontum": "kon-tum",
    "đắk nông": "dak-nong", "dak nong": "dak-nong",

    # ── Vietnam: Southern Region & Mekong Delta ───────────────────────────────
    "hồ chí minh": "ho-chi-minh", "ho chi minh": "ho-chi-minh",
    "hcm": "ho-chi-minh", "hcmc": "ho-chi-minh", "saigon": "ho-chi-minh",
    "sài gòn": "ho-chi-minh", "sai gon": "ho-chi-minh", "tphcm": "ho-chi-minh",
    "tp hcm": "ho-chi-minh", "tp.hcm": "ho-chi-minh", "ho chi minh city": "ho-chi-minh",

    "bà rịa": "ba-ria-vung-tau", "ba ria": "ba-ria-vung-tau",
    "vũng tàu": "ba-ria-vung-tau", "vung tau": "ba-ria-vung-tau", "vungtau": "ba-ria-vung-tau",
    "côn đảo": "ba-ria-vung-tau", "con dao": "ba-ria-vung-tau",

    "kiên giang": "kien-giang", "kien giang": "kien-giang",
    "phú quốc": "kien-giang", "phu quoc": "kien-giang", "phuquoc": "kien-giang",
    "hà tiên": "kien-giang", "ha tien": "kien-giang",

    "cần thơ": "can-tho", "can tho": "can-tho", "cantho": "can-tho",
    "bến ninh kiều": "can-tho", "ben ninh kieu": "can-tho", "cái răng": "can-tho", "cai rang": "can-tho",

    "mekong": "mekong", "mekong delta": "mekong",
    "đồng bằng sông cửu long": "mekong", "dong bang song cuu long": "mekong",
    "miền tây": "mekong", "mien tay": "mekong", "tây nam bộ": "mekong", "tay nam bo": "mekong",

    "bến tre": "ben-tre", "ben tre": "ben-tre",
    "tiền giang": "tien-giang", "tien giang": "tien-giang", "mỹ tho": "tien-giang", "my tho": "tien-giang",
    "đồng tháp": "dong-thap", "dong thap": "dong-thap", "sa đéc": "dong-thap", "sa dec": "dong-thap",
    "vĩnh long": "vinh-long", "vinh long": "vinh-long",
    "an giang": "an-giang", "châu đốc": "an-giang", "chau doc": "an-giang", "long xuyên": "an-giang", "long xuyen": "an-giang",
    "sóc trăng": "soc-trang", "soc trang": "soc-trang",
    "bạc liêu": "bac-lieu", "bac lieu": "bac-lieu",
    "cà mau": "ca-mau", "ca mau": "ca-mau",
    "hậu giang": "hau-giang", "hau giang": "hau-giang",
    "trà vinh": "tra-vinh", "tra vinh": "tra-vinh",
    "tây ninh": "tay-ninh", "tay ninh": "tay-ninh",
    "bình dương": "binh-duong", "binh duong": "binh-duong",
    "đồng nai": "dong-nai", "dong nai": "dong-nai",
    "long an": "long-an", "long an": "long-an",
    "bình phước": "binh-phuoc", "binh phuoc": "binh-phuoc",

    # ── Cambodia ─────────────────────────────────────────────────────────────
    "siem reap": "siem-reap", "siemreap": "siem-reap", "siem-reap": "siem-reap",
    "angkor": "siem-reap", "angkor wat": "siem-reap", "angkor thom": "siem-reap",
    "phnom penh": "phnom-penh", "phnompenh": "phnom-penh", "phnom-penh": "phnom-penh",

    # ── Laos ─────────────────────────────────────────────────────────────────
    "luang prabang": "luang-prabang", "luangprabang": "luang-prabang", "luang-prabang": "luang-prabang",
    "vientiane": "vientiane",

    # ── Thailand ─────────────────────────────────────────────────────────────
    "bangkok": "bangkok", "krung thep": "bangkok",
    "chiang mai": "chiang-mai", "chiangmai": "chiang-mai", "chiang-mai": "chiang-mai",
    "phuket": "phuket",
}


def normalize_destination_text(text: str | None) -> str:
    """Normalize input text for comparison (lowercase, strip, replace hyphens and normalize spaces)."""
    if not text:
        return ""
    cleaned = (text or "").casefold().replace("-", " ")
    return " ".join(cleaned.split())


def match_destination_slug(location: str | None) -> str | None:
    """Deterministic, pure-Python destination slug matcher.

    Resolution Strategy:
    1. If already a valid canonical slug (e.g. "ha-noi", "quang-ninh"), return it.
    2. Check Country Gateways (e.g. "vietnam" -> "ha-noi", "cambodia" -> "siem-reap").
    3. Check Exact match in DESTINATION_KEYWORD_MAP.
    4. Longest-match substring scan across DESTINATION_KEYWORD_MAP.
    5. Return None if no match found.
    """
    if not location:
        return None

    raw_clean = location.strip().lower()
    normalized = normalize_destination_text(location)

    # 1. Direct valid slug check
    slug_candidate = raw_clean.replace(" ", "-")
    if slug_candidate in VALID_DESTINATION_SLUGS:
        return slug_candidate
    if raw_clean in VALID_DESTINATION_SLUGS:
        return raw_clean

    # 2. Country-level gateway mapping
    if raw_clean in COUNTRY_GATEWAY_MAP:
        return COUNTRY_GATEWAY_MAP[raw_clean]
    if normalized in COUNTRY_GATEWAY_MAP:
        return COUNTRY_GATEWAY_MAP[normalized]

    # 3. Exact match in keyword map
    if raw_clean in DESTINATION_KEYWORD_MAP:
        return DESTINATION_KEYWORD_MAP[raw_clean]
    if normalized in DESTINATION_KEYWORD_MAP:
        return DESTINATION_KEYWORD_MAP[normalized]

    # 4. Longest-match substring scan (prioritize specific landmarks over generic words)
    best_match: str | None = None
    best_len = 0
    for keyword, slug in DESTINATION_KEYWORD_MAP.items():
        if (keyword in raw_clean or keyword in normalized) and len(keyword) > best_len:
            best_match = slug
            best_len = len(keyword)

    if best_match:
        return best_match

    # 5. Check if any country keyword is inside the string (e.g. "Tour in Vietnam")
    for country_kw, gateway_slug in COUNTRY_GATEWAY_MAP.items():
        if country_kw in raw_clean or country_kw in normalized:
            return gateway_slug

    return None

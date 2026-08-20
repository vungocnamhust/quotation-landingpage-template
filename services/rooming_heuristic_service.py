from __future__ import annotations

import math
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.rooming_heuristic import RoomingHeuristicRule
from repositories.rooming_heuristic_repository import RoomingHeuristicRepository


DEFAULT_ROOMING_RULES: list[dict[str, Any]] = [
    {
        "id": "rule_solo_traveler",
        "name": "Solo Traveler",
        "description": "Single adult with no children",
        "min_adults": 1,
        "max_adults": 1,
        "min_children": 0,
        "max_children": 0,
        "min_infants": 0,
        "max_infants": 0,
        "kid_age_condition": "NO_KIDS",
        "suggestions": [
            {
                "en": "1 Single Room",
                "vi": "1 Phòng Đơn (Single Room)",
                "ar": "غرفة مفردة واحدة",
                "code": "1_single",
            },
            {
                "en": "1 Double (Single Occupancy)",
                "vi": "1 Phòng Double (Sử dụng 1 người)",
                "ar": "غرفة مزدوجة (إشغال فردي)",
                "code": "1_double_single_occ",
            },
        ],
        "min_rooms_formula": "1",
        "priority": 100,
        "is_active": True,
    },
    {
        "id": "rule_couple_no_kids",
        "name": "Couple / Pair",
        "description": "Two adults with no children",
        "min_adults": 2,
        "max_adults": 2,
        "min_children": 0,
        "max_children": 0,
        "min_infants": 0,
        "max_infants": 0,
        "kid_age_condition": "NO_KIDS",
        "suggestions": [
            {
                "en": "1 Double (King Bed)",
                "vi": "1 Phòng Double (Giường King)",
                "ar": "غرفة مزدوجة (سرير كينج)",
                "code": "1_double_king",
            },
            {
                "en": "1 Twin (2 Separate Beds)",
                "vi": "1 Phòng Twin (2 Giường đơn tách biệt)",
                "ar": "غرفة توأم (سريرين منفصلين)",
                "code": "1_twin",
            },
        ],
        "min_rooms_formula": "1",
        "priority": 90,
        "is_active": True,
    },
    {
        "id": "rule_family_young_kids",
        "name": "Couple with Young Kids",
        "description": "Two adults with 1-2 young children (all under 12 years)",
        "min_adults": 2,
        "max_adults": 2,
        "min_children": 1,
        "max_children": 2,
        "min_infants": 0,
        "max_infants": 2,
        "kid_age_condition": "ALL_UNDER_12",
        "suggestions": [
            {
                "en": "1 Double Room + Extra Bed",
                "vi": "1 Phòng Double + Kê thêm giường phụ",
                "ar": "غرفة مزدوجة + سرير إضافي",
                "code": "1_double_extra_bed",
            },
            {
                "en": "1 Double + 1 Twin (Connecting)",
                "vi": "1 Double + 1 Twin (Phòng thông nhau)",
                "ar": "غرفة مزدوجة + غرفة توأم متصلة",
                "code": "1_double_1_twin_connecting",
            },
            {
                "en": "1 Family Suite / Villa",
                "vi": "1 Căn Family Suite / Villa",
                "ar": "جناح عائلي / فيلا",
                "code": "family_suite",
            },
        ],
        "min_rooms_formula": "1",
        "priority": 80,
        "is_active": True,
    },
    {
        "id": "rule_family_teen_kids",
        "name": "Couple with Teen Kids",
        "description": "Two adults with children where at least one is 12+ years",
        "min_adults": 2,
        "max_adults": 2,
        "min_children": 1,
        "max_children": 3,
        "min_infants": 0,
        "max_infants": 2,
        "kid_age_condition": "ANY_12_AND_ABOVE",
        "suggestions": [
            {
                "en": "1 Double + 1 Twin (Connecting)",
                "vi": "1 Double + 1 Twin (Phòng thông nhau)",
                "ar": "غرفة مزدوجة + غرفة توأم متصلة",
                "code": "1_double_1_twin_connecting",
            },
            {
                "en": "2 Interconnecting Rooms",
                "vi": "2 Phòng thông nhau (Interconnecting)",
                "ar": "غرفتان متصلتان",
                "code": "2_interconnecting",
            },
            {
                "en": "1 Family Suite / Villa",
                "vi": "1 Căn Family Suite / Villa",
                "ar": "جناح عائلي / فيلا",
                "code": "family_suite",
            },
        ],
        "min_rooms_formula": "2",
        "priority": 75,
        "is_active": True,
    },
    {
        "id": "rule_three_adults",
        "name": "Three Adults",
        "description": "Three adults travelling together",
        "min_adults": 3,
        "max_adults": 3,
        "min_children": 0,
        "max_children": 0,
        "min_infants": 0,
        "max_infants": 0,
        "kid_age_condition": "NO_KIDS",
        "suggestions": [
            {
                "en": "1 Double + 1 Single",
                "vi": "1 Phòng Double + 1 Phòng Single",
                "ar": "غرفة مزدوجة + غرفة مفردة",
                "code": "1_double_1_single",
            },
            {
                "en": "1 Triple Room / Suite",
                "vi": "1 Phòng Ba người (Triple Room/Suite)",
                "ar": "غرفة ثلاثية / جناح",
                "code": "1_triple",
            },
            {
                "en": "3 Single Rooms",
                "vi": "3 Phòng Đơn riêng biệt",
                "ar": "3 غرف مفردة",
                "code": "3_single",
            },
        ],
        "min_rooms_formula": "2",
        "priority": 70,
        "is_active": True,
    },
    {
        "id": "rule_quad_adults",
        "name": "Adult Group (4+ Adults)",
        "description": "Four or more adults with no children",
        "min_adults": 4,
        "max_adults": None,
        "min_children": 0,
        "max_children": 0,
        "min_infants": 0,
        "max_infants": 0,
        "kid_age_condition": "NO_KIDS",
        "suggestions": [
            {
                "en": "{rooms} Double Rooms",
                "vi": "{rooms} Phòng Double",
                "ar": "{rooms} غرف مزدوجة",
                "code": "n_double_rooms",
            },
            {
                "en": "{rooms} Twin Rooms",
                "vi": "{rooms} Phòng Twin",
                "ar": "{rooms} غرف توأم",
                "code": "n_twin_rooms",
            },
            {
                "en": "Multi-bedroom Private Villa",
                "vi": "Villa riêng nhiều phòng ngủ",
                "ar": "فيلا خاصة متعددة غرف النوم",
                "code": "private_villa",
            },
        ],
        "min_rooms_formula": "ceil(adults / 2)",
        "priority": 60,
        "is_active": True,
    },
    {
        "id": "rule_large_family_multigen",
        "name": "Large Family / Multi-gen Group",
        "description": "Family or multi-generational party with adults and children",
        "min_adults": 1,
        "max_adults": None,
        "min_children": 1,
        "max_children": None,
        "min_infants": 0,
        "max_infants": None,
        "kid_age_condition": "ANY",
        "suggestions": [
            {
                "en": "{rooms} Rooms (Connecting/Adjoining)",
                "vi": "{rooms} Phòng (Thông nhau / Cạnh nhau)",
                "ar": "{rooms} غرف (متصلة / متجاورة)",
                "code": "n_rooms_connecting",
            },
            {
                "en": "Family Suite / Multi-bedroom Villa",
                "vi": "Family Suite / Villa nhiều phòng ngủ",
                "ar": "جناح عائلي / فيلا متعددة غرف النوم",
                "code": "family_suite_villa",
            },
            {
                "en": "{adults} Double + Connecting Kids Room",
                "vi": "{adults} Phòng Double + Phòng Trẻ em thông nhau",
                "ar": "{adults} مزدوجة + غرفة أطفال متصلة",
                "code": "adults_double_connecting_kids",
            },
        ],
        "min_rooms_formula": "ceil(adults / 2) + ceil(children / 2)",
        "priority": 10,
        "is_active": True,
    },
]


def calculate_min_rooms(adults: int, children: int, formula: str | None = None) -> int:
    """Calculate minimum required rooms based on formula or standard capacity heuristics."""
    safe_adults = max(1, adults)
    safe_kids = max(0, children)

    if formula == "1":
        return 1
    if formula == "2":
        return 2
    if formula == "ceil(adults / 2)":
        return math.ceil(safe_adults / 2)

    # Standard default heuristic
    return math.ceil(safe_adults / 2) + math.ceil(safe_kids / 2)


def format_suggestion_template(template: str, adults: int, children: int, rooms: int) -> str:
    """Interpolate dynamic variables in suggestion templates."""
    return (
        template.replace("{adults}", str(adults))
        .replace("{children}", str(children))
        .replace("{rooms}", str(rooms))
    )


class RoomingHeuristicService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RoomingHeuristicRepository(session)

    async def get_active_rules(self) -> list[RoomingHeuristicRule]:
        rules = await self.repo.list_active()
        if not rules:
            await self.seed_default_rules()
            rules = await self.repo.list_active()
        return rules

    async def seed_default_rules(self) -> list[RoomingHeuristicRule]:
        seeded: list[RoomingHeuristicRule] = []
        for r in DEFAULT_ROOMING_RULES:
            rule = await self.repo.upsert(
                rule_id=r["id"],
                name=r["name"],
                description=r["description"],
                min_adults=r["min_adults"],
                max_adults=r["max_adults"],
                min_children=r["min_children"],
                max_children=r["max_children"],
                min_infants=r["min_infants"],
                max_infants=r["max_infants"],
                kid_age_condition=r["kid_age_condition"],
                suggestions=r["suggestions"],
                min_rooms_formula=r["min_rooms_formula"],
                priority=r["priority"],
                is_active=r["is_active"],
            )
            seeded.append(rule)
        return seeded

    async def evaluate(
        self,
        adults: int = 2,
        children: int = 0,
        kid_ages: list[int] | None = None,
        infants: int = 0,
        lang: str = "en",
    ) -> dict[str, Any]:
        """Match rules and evaluate rooming suggestions for given party demographics."""
        safe_adults = max(1, adults)
        safe_kids = max(0, children)
        safe_infants = max(0, infants)

        # Normalize kid_ages length
        safe_ages = list(kid_ages or [])
        while len(safe_ages) < safe_kids:
            safe_ages.append(6)
        safe_ages = safe_ages[:safe_kids]

        rules = await self.get_active_rules()

        for rule in rules:
            # 1. Adult bounds
            if safe_adults < rule.min_adults:
                continue
            if rule.max_adults is not None and safe_adults > rule.max_adults:
                continue

            # 2. Children bounds
            if safe_kids < rule.min_children:
                continue
            if rule.max_children is not None and safe_kids > rule.max_children:
                continue

            # 3. Infant bounds
            if safe_infants < rule.min_infants:
                continue
            if rule.max_infants is not None and safe_infants > rule.max_infants:
                continue

            # 4. Kid age condition
            if rule.kid_age_condition == "NO_KIDS" and safe_kids > 0:
                continue
            if rule.kid_age_condition == "ALL_UNDER_12":
                if safe_kids == 0 or not all(age < 12 for age in safe_ages):
                    continue
            if rule.kid_age_condition == "ANY_12_AND_ABOVE":
                if safe_kids == 0 or not any(age >= 12 for age in safe_ages):
                    continue

            # Rule matched!
            min_rooms = calculate_min_rooms(safe_adults, safe_kids, rule.min_rooms_formula)
            lang_key = lang if lang in ("en", "vi", "ar") else "en"

            formatted_suggestions: list[str] = []
            for item in rule.suggestions:
                raw_text = item.get(lang_key) or item.get("en") or ""
                if raw_text:
                    formatted_text = format_suggestion_template(
                        raw_text, safe_adults, safe_kids, min_rooms
                    )
                    formatted_suggestions.append(formatted_text)

            return {
                "matched_rule_id": rule.id,
                "matched_rule_name": rule.name,
                "min_estimated_rooms": min_rooms,
                "suggestions": formatted_suggestions,
            }

        # Fallback if no specific rule matched
        fallback_rooms = math.ceil(safe_adults / 2) + math.ceil(safe_kids / 2)
        fallback_suggestion = (
            f"{fallback_rooms} Phòng" if lang == "vi" else f"{fallback_rooms} Rooms"
        )
        return {
            "matched_rule_id": None,
            "matched_rule_name": "Fallback General Capacity",
            "min_estimated_rooms": fallback_rooms,
            "suggestions": [fallback_suggestion],
        }

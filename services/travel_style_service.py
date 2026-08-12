from __future__ import annotations

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.travel_style_repository import TravelStyleRepository

CATEGORY_METADATA = {
    "group_composition": {
        "title_en": "Group Composition",
        "title_vi": "Du lịch theo nhóm",
        "display_order": 1,
    },
    "tour_type": {
        "title_en": "Tour Type",
        "title_vi": "Loại hình tour",
        "display_order": 2,
    },
    "purpose": {
        "title_en": "Purpose & Theme",
        "title_vi": "Mục đích chuyến đi",
        "display_order": 3,
    },
    "interest_experience": {
        "title_en": "Interest & Experience",
        "title_vi": "Sở thích & Trải nghiệm",
        "display_order": 4,
    },
}


class TravelStyleService:
    """Service layer for Travel Style taxonomy logic and data normalization."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = TravelStyleRepository(session)

    async def get_grouped_travel_styles(self) -> Dict[str, Any]:
        """Fetch all active travel style tags grouped by category."""
        tags = await self.repo.list_active_tags()

        # Fallback if DB is empty / unmigrated yet: return built-in standard taxonomy
        categories_map: Dict[str, List[Dict[str, Any]]] = {cat: [] for cat in CATEGORY_METADATA}

        for tag in tags:
            cat_key = tag.category
            if cat_key not in categories_map:
                categories_map[cat_key] = []
            categories_map[cat_key].append({
                "id": tag.id,
                "category": tag.category,
                "name_en": tag.name_en,
                "name_vi": tag.name_vi,
                "slug": tag.slug,
                "display_order": tag.display_order,
            })

        result_categories = []
        for cat_key, meta in sorted(CATEGORY_METADATA.items(), key=lambda item: item[1]["display_order"]):
            result_categories.append({
                "category_id": cat_key,
                "title_en": meta["title_en"],
                "title_vi": meta["title_vi"],
                "tags": categories_map.get(cat_key, []),
            })

        return {"categories": result_categories}

    @staticmethod
    def sync_travel_style_facts(customer_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Bidirectional sync helper between travel_style and guest_profile in customer_facts."""
        if not isinstance(customer_facts, dict):
            return customer_facts

        travel_style = customer_facts.get("travel_style") or customer_facts.get("guest_profile") or ""
        customer_facts["travel_style"] = travel_style
        customer_facts["guest_profile"] = travel_style
        return customer_facts

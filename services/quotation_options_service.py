"""Read model for the quotation-intake options endpoint."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from editable_brochure_contract import editable_contract_payload
from repositories import BrandRepository
from repositories.travel_designer_repository import TravelDesignerRepository


async def get_quotation_options(session: AsyncSession) -> dict[str, Any]:
    designers = await TravelDesignerRepository(session).list_profiles(active_only=True)
    active_brands = await BrandRepository(session).list_active()
    brands = [{"id": item.id, "label": item.display_name} for item in active_brands]
    return {
        "brands": brands,
        "templates": [{"id": "quote-generator", "label": "Brochure", "brandIds": [item["id"] for item in brands]}],
        "languages": [{"id": value, "label": value.upper()} for value in ("en", "vi", "ar")],
        "travelDesigners": [
            {"id": item.id, "name": item.name, "email": item.email, "phone": item.phone, "imageUrl": item.image_url}
            for item in designers
        ],
        "editableContract": editable_contract_payload(),
    }

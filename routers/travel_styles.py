from __future__ import annotations

from typing import Annotated, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.travel_style_service import TravelStyleService

router = APIRouter(prefix="/api/v2", tags=["travel-styles"])


class TravelStyleTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    name_en: str
    name_vi: str
    slug: str
    display_order: int


class TravelStyleCategoryGroupResponse(BaseModel):
    category_id: str
    title_en: str
    title_vi: str
    tags: List[TravelStyleTagResponse]


class TravelStyleResponse(BaseModel):
    categories: List[TravelStyleCategoryGroupResponse]


DBDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/travel-styles")
async def get_travel_styles(db: DBDep) -> TravelStyleResponse:
    """Get active travel style tags grouped by category taxonomy."""
    service = TravelStyleService(db)
    result = await service.get_grouped_travel_styles()
    return TravelStyleResponse.model_validate(result)

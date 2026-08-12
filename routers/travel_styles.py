from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.travel_style_service import TravelStyleService

router = APIRouter(prefix="/api/v2", tags=["travel-styles"])


@router.get("/travel-styles")
async def get_travel_styles(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get active travel style tags grouped by category taxonomy."""
    service = TravelStyleService(db)
    return await service.get_grouped_travel_styles()

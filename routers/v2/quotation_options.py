"""Quotation intake option catalog routes."""
from __future__ import annotations

from fastapi import APIRouter

from api.dependencies import DbSessionDep, EditorPrincipalDep
from services.quotation_options_service import get_quotation_options

router = APIRouter(prefix="/api/v2", tags=["quotation-options"])


@router.get("/quotation-options")
async def get_quotation_options_v2(
    db: DbSessionDep,
    _principal: EditorPrincipalDep,
) -> dict:
    return await get_quotation_options(db)

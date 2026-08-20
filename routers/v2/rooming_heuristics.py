from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from schemas.v2.rooming_heuristic import (
    RoomingEvaluationRequestSchema,
    RoomingEvaluationResponseSchema,
    RoomingHeuristicRuleResponseSchema,
    RoomingHeuristicsListResponseSchema,
)
from services.rooming_heuristic_service import RoomingHeuristicService

router = APIRouter(prefix="/api/v2/rooming-heuristics", tags=["rooming-heuristics"])

DBDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=RoomingHeuristicsListResponseSchema)
async def list_rooming_heuristics(db: DBDep) -> RoomingHeuristicsListResponseSchema:
    """Retrieve all active rooming configuration heuristic rules with multilingual suggestions."""
    service = RoomingHeuristicService(db)
    rules = await service.get_active_rules()
    items = [RoomingHeuristicRuleResponseSchema.model_validate(r) for r in rules]
    return RoomingHeuristicsListResponseSchema(items=items, total=len(items))


@router.post("/evaluate", response_model=RoomingEvaluationResponseSchema)
async def evaluate_rooming_heuristics(
    request: RoomingEvaluationRequestSchema,
    db: DBDep,
) -> RoomingEvaluationResponseSchema:
    """Evaluate rooming suggestions for given guest demographics and kid ages in real time."""
    service = RoomingHeuristicService(db)
    result = await service.evaluate(
        adults=request.adults,
        children=request.children,
        kid_ages=request.kid_ages,
        infants=request.infants,
        lang=request.lang,
    )
    return RoomingEvaluationResponseSchema.model_validate(result)

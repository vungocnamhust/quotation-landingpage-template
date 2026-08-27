"""V2 rate routes (15.3) — nested under products + rate-id operations, one file (§1.6)."""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from api.dependencies import DbSessionDep, EditorPrincipalDep
from core.kernel import ActorRef
from schemas.v2.rate import (
    RateCreateSchema,
    RateListResponseSchema,
    RateResponseSchema,
    RateSupersedeSchema,
    RateUpdateSchema,
)
from services.rate_service import RateConflictError, RateService, RateValidationError

router = APIRouter(tags=["rates"])


def _actor_from_principal(principal: EditorPrincipalDep) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


@router.get("/api/v2/products/{product_id}/rates", response_model=RateListResponseSchema)
async def list_product_rates(
    product_id: str,
    session: DbSessionDep,
    lifecycle: Annotated[Literal["draft", "active", "superseded", "expired", "all"], Query()] = "active",
    on_date: Annotated[date | None, Query(description="Filter rates covering this local date")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    principal: EditorPrincipalDep = None,
) -> RateListResponseSchema:
    service = RateService(session)
    result = await service.list_rates_for_product(
        product_id, lifecycle=None if lifecycle == "all" else lifecycle, on_date=on_date, limit=limit
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' was not found.")
    items, total = result
    return RateListResponseSchema(items=items, total=total)


@router.post("/api/v2/products/{product_id}/rates", response_model=RateResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_product_rate(
    product_id: str,
    payload: RateCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> RateResponseSchema:
    service = RateService(session)
    try:
        rate = await service.create_draft(product_id, payload, actor=_actor_from_principal(principal))
        if rate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' was not found.")
        await session.commit()
        return rate
    except RateValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err


@router.get("/api/v2/rates/{rate_id}", response_model=RateResponseSchema)
async def get_rate(
    rate_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> RateResponseSchema:
    service = RateService(session)
    rate = await service.get_rate(rate_id)
    if rate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate '{rate_id}' was not found.")
    return rate


@router.put("/api/v2/rates/{rate_id}", response_model=RateResponseSchema)
async def update_rate(
    rate_id: str,
    payload: RateUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> RateResponseSchema:
    service = RateService(session)
    try:
        rate = await service.update_draft(rate_id, payload, actor=_actor_from_principal(principal))
        if rate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate '{rate_id}' was not found.")
        await session.commit()
        return rate
    except RateConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except RateValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err


@router.delete("/api/v2/rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft_rate(
    rate_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> None:
    service = RateService(session)
    try:
        deleted = await service.delete_draft(rate_id)
        if deleted is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate '{rate_id}' was not found.")
        await session.commit()
    except RateConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.post("/api/v2/rates/{rate_id}/activate", response_model=RateResponseSchema)
async def activate_rate(
    rate_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> RateResponseSchema:
    service = RateService(session)
    try:
        rate = await service.activate(rate_id, actor=_actor_from_principal(principal))
        if rate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate '{rate_id}' was not found.")
        await session.commit()
        return rate
    except RateConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except RateValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err


@router.post("/api/v2/rates/{rate_id}/supersede", response_model=RateResponseSchema, status_code=status.HTTP_201_CREATED)
async def supersede_rate(
    rate_id: str,
    payload: RateSupersedeSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> RateResponseSchema:
    service = RateService(session)
    try:
        rate = await service.supersede(rate_id, payload, actor=_actor_from_principal(principal))
        if rate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rate '{rate_id}' was not found.")
        await session.commit()
        return rate
    except RateConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except RateValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err

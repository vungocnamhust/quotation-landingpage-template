"""V2 partners catalog routes."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import DbSessionDep, EditorPrincipalDep
from schemas.v2.partner import (
    PartnerProfileCreateSchema,
    PartnerProfileListResponseSchema,
    PartnerProfileResponseSchema,
    PartnerProfileUpdateSchema,
)
from services.partner_service import PartnerService

router = APIRouter(prefix="/api/v2/partners", tags=["partners"])


@router.get("", response_model=PartnerProfileListResponseSchema)
async def list_partners(
    session: DbSessionDep,
    active: Annotated[Literal["true", "false", "all"], Query(description="Filter by active status")] = "true",
    search: Annotated[str, Query(description="Search by company name, contact name, or email")] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    principal: EditorPrincipalDep = None,
) -> PartnerProfileListResponseSchema:
    service = PartnerService(session)
    items, total = await service.list_partners(active=active, search=search, limit=limit)
    return PartnerProfileListResponseSchema(items=items, total=total)


@router.post("", response_model=PartnerProfileResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_partner(
    payload: PartnerProfileCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> PartnerProfileResponseSchema:
    service = PartnerService(session)
    try:
        partner = await service.create_partner(payload)
        await session.commit()
        return partner
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.get("/{partner_id}", response_model=PartnerProfileResponseSchema)
async def get_partner(
    partner_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> PartnerProfileResponseSchema:
    service = PartnerService(session)
    partner = await service.get_partner(partner_id)
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner was not found.")
    return partner


@router.put("/{partner_id}", response_model=PartnerProfileResponseSchema)
async def update_partner(
    partner_id: str,
    payload: PartnerProfileUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> PartnerProfileResponseSchema:
    service = PartnerService(session)
    try:
        partner = await service.update_partner(partner_id, payload)
        if partner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner was not found.")
        await session.commit()
        return partner
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.patch("/{partner_id}/status", response_model=PartnerProfileResponseSchema)
async def set_partner_status(
    partner_id: str,
    payload: dict[str, bool],
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> PartnerProfileResponseSchema:
    if "isActive" not in payload and "is_active" not in payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="isActive is required")
    is_active = bool(payload.get("isActive", payload.get("is_active", True)))

    service = PartnerService(session)
    partner = await service.set_status(partner_id, is_active=is_active)
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner was not found.")
    await session.commit()
    return partner

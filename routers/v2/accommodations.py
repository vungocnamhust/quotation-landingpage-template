"""V2 accommodation catalog routes."""
from __future__ import annotations

from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import Principal, require_editor
from repositories.accommodation_repository import AccommodationRepository


router = APIRouter(prefix="/api/v2/accommodations", tags=["accommodations"])


class AccommodationProfileRequest(BaseModel):
    destinationId: str
    name: str
    room_type: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    intro: str | None = None
    phone: str | None = None
    display_city: str | None = None
    display_date: str | None = None
    hotel_asset: str | None = None
    room_asset: str | None = None


class AccommodationStatusRequest(BaseModel):
    isActive: bool


def _get_helpers():
    import main
    return main


@router.get("")
async def list_accommodations(
    active: Literal["true", "false", "all"] = "true",
    query: str = "",
    destinationId: str | None = None,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        await h._seed_destination_catalog(session)
        items = await AccommodationRepository(session).list_profiles(
            active_only={"true": True, "false": False, "all": None}[active],
            search=query,
            destination_id=destinationId,
        )
        return {"items": [await h._serialize_accommodation(item, session) for item in items]}


@router.get("/{profile_id}")
async def get_accommodation(profile_id: str, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        profile = await AccommodationRepository(session).get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Accommodation profile was not found.")
        return await h._serialize_accommodation(profile, session)


@router.post("", status_code=201)
async def create_accommodation(payload: AccommodationProfileRequest, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        saved = await h._save_accommodation_profile(session, payload)
        await session.commit()
        return saved


@router.put("/{profile_id}")
async def update_accommodation(profile_id: str, payload: AccommodationProfileRequest, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        profile = await AccommodationRepository(session).get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Accommodation profile was not found.")
        saved = await h._save_accommodation_profile(session, payload, profile)
        await session.commit()
        return saved


@router.patch("/{profile_id}/status")
async def update_accommodation_status(profile_id: str, payload: AccommodationStatusRequest, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        profile = await AccommodationRepository(session).get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Accommodation profile was not found.")
        saved = await AccommodationRepository(session).set_status(profile, is_active=payload.isActive)
        await session.commit()
        return await h._serialize_accommodation(saved, session)

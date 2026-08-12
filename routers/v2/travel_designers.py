"""V2 travel designers catalog routes."""
from __future__ import annotations

import uuid
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from core.auth import Principal, require_editor
from repositories.travel_designer_repository import TravelDesignerRepository
from services.media_locations import storage_slug


router = APIRouter(prefix="/api/v2/travel-designers", tags=["travel-designers"])


class TravelDesignerProfileRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    imageR2Key: str | None = None


class TravelDesignerBrandDefaultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    designerProfileId: str | None = None


def _get_helpers():
    import main
    return main


@router.get("")
async def list_travel_designers(
    request: Request,
    active: Literal["true", "false", "all"] = "true",
    search: str = "",
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        items = await TravelDesignerRepository(session).list_profiles(
            active_only={"true": True, "false": False, "all": None}[active],
            search=search,
        )
        return {"items": [h._serialize_travel_designer(item) for item in items]}


@router.post("", status_code=201)
async def create_travel_designer(payload: TravelDesignerProfileRequest, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        repository = TravelDesignerRepository(session)
        if await repository.get_by_email(payload.email):
            raise HTTPException(status_code=409, detail="A Travel Designer already uses this email.")
        profile = await repository.create_profile(
            profile_id=f"td_{uuid.uuid4().hex[:12]}",
            email=payload.email,
            name=payload.name,
            phone=payload.phone,
            storage_slug=storage_slug(payload.email.split("@", 1)[0]),
            image_r2_key=payload.imageR2Key,
        )
        await session.commit()
        await session.refresh(profile)
        return h._serialize_travel_designer(profile)


@router.put("/{profile_id}")
async def update_travel_designer(profile_id: str, payload: TravelDesignerProfileRequest, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        repository = TravelDesignerRepository(session)
        profile = await repository.get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Travel Designer profile was not found.")
        profile = await repository.update_profile(
            profile,
            email=payload.email,
            name=payload.name,
            phone=payload.phone,
            storage_slug=storage_slug(payload.email.split("@", 1)[0]),
            image_r2_key=payload.imageR2Key,
        )
        await session.commit()
        await session.refresh(profile)
        return h._serialize_travel_designer(profile)


@router.patch("/{profile_id}/status")
async def set_travel_designer_status(
    profile_id: str,
    payload: dict[str, bool],
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    if "isActive" not in payload:
        raise HTTPException(status_code=422, detail="isActive is required")
    async with h._get_db_session_factory()() as session:
        repository = TravelDesignerRepository(session)
        profile = await repository.get_profile(profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Travel Designer profile was not found.")
        profile = await repository.set_status(profile, is_active=bool(payload["isActive"]))
        await session.commit()
        await session.refresh(profile)
        return h._serialize_travel_designer(profile)

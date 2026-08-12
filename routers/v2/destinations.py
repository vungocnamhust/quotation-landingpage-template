"""V2 destinations catalog routes."""
from __future__ import annotations

from typing import Annotated, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from core.auth import Principal, require_editor, require_quote_admin
from repositories.destination_repository import DestinationRepository


router = APIRouter(prefix="/api/v2/destinations", tags=["destinations"])


class DestinationCatalogRequest(BaseModel):
    canonicalName: str
    slug: str
    aliases: list[str] = Field(default_factory=list)
    countrySlug: str | None = None
    regionSlug: str | None = None
    provinceSlug: str | None = None
    latitude: float
    longitude: float

    @field_validator("canonicalName", "slug")
    @classmethod
    def require_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("must be between -180 and 180")
        return value


class DestinationStatusRequest(BaseModel):
    isActive: bool


def _get_helpers():
    import main
    return main


@router.get("")
async def search_destinations(query: str = "", limit: int = 20, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        await h._seed_destination_catalog(session)
        await session.commit()
        rows = await DestinationRepository(session).search(query, limit=max(1, min(limit, 50)))
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for item, alias in rows:
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            items.append(await h._serialize_destination(DestinationRepository(session), item, matched_from=alias))
        return {"items": items}


@router.get("/{destination_id}")
async def get_destination(destination_id: str, principal: Principal = Depends(require_editor)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        await h._seed_destination_catalog(session)
        item = await DestinationRepository(session).get(destination_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Destination was not found.")
        return await h._serialize_destination(DestinationRepository(session), item)


@router.post("", status_code=201)
async def create_destination(payload: DestinationCatalogRequest, principal: Principal = Depends(require_quote_admin)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        saved = await h._save_destination(session, payload)
        await session.commit()
        return await h._serialize_destination(DestinationRepository(session), saved)


@router.put("/{destination_id}")
async def update_destination(destination_id: str, payload: DestinationCatalogRequest, principal: Principal = Depends(require_quote_admin)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        item = await DestinationRepository(session).get(destination_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Destination was not found.")
        saved = await h._save_destination(session, payload, item)
        await session.commit()
        return await h._serialize_destination(DestinationRepository(session), saved)


@router.patch("/{destination_id}/status")
async def update_destination_status(destination_id: str, payload: DestinationStatusRequest, principal: Principal = Depends(require_quote_admin)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        repository = DestinationRepository(session)
        item = await repository.get(destination_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Destination was not found.")
        if payload.isActive and (item.latitude is None or item.longitude is None):
            raise HTTPException(
                status_code=422,
                detail={"message": "An active destination requires coordinates.", "missingInputs": ["latitude", "longitude"]},
            )
        saved = await repository.set_status(item, is_active=payload.isActive)
        await session.commit()
        return await h._serialize_destination(repository, saved)

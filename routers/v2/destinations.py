"""V2 destinations catalog routes."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from core.auth import Principal, require_editor, require_quote_admin
from core.rules.catalog_vocab import DESTINATION_TYPE
from repositories.destination_repository import DestinationReactivationError, DestinationRepository


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
    mediaPrefix: str | None = None
    parentId: str | None = None
    destinationType: str | None = None
    countryCode: str | None = Field(default=None, min_length=2, max_length=2)
    iataCode: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = None

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

    @field_validator("destinationType")
    @classmethod
    def validate_destination_type(cls, value: str | None) -> str | None:
        if value is not None and value not in DESTINATION_TYPE:
            raise ValueError(f"must be one of {sorted(DESTINATION_TYPE)}")
        return value

    @field_validator("countryCode")
    @classmethod
    def validate_country_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("iataCode")
    @classmethod
    def validate_iata_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from zoneinfo import available_timezones

        if value not in available_timezones():
            raise ValueError(f"'{value}' is not a valid IANA timezone")
        return value


class DestinationStatusRequest(BaseModel):
    isActive: bool


class DestinationMergeRequest(BaseModel):
    targetId: str = Field(min_length=1)


def _get_helpers():
    import main
    return main


@router.get("")
async def search_destinations(
    query: str = "",
    active: str = "true",
    countrySlug: str | None = None,
    types: str | None = None,
    parentId: str | None = None,
    limit: int = 20,
    principal: Principal = Depends(require_editor),
):
    h = _get_helpers()
    destination_types = None
    if types:
        requested = {value.strip() for value in types.split(",") if value.strip()}
        invalid = requested - DESTINATION_TYPE
        if invalid:
            raise HTTPException(status_code=422, detail={"message": f"Unknown destination type(s): {sorted(invalid)}"})
        destination_types = list(requested)
    async with h._get_db_session_factory()() as session:
        await h._seed_destination_catalog(session)
        await session.commit()
        rows = await DestinationRepository(session).search(
            query,
            active=active,
            country_slug=countrySlug,
            destination_types=destination_types,
            parent_id=parentId,
            limit=max(1, min(limit, 200)),
        )
        items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for item, alias, is_merge_alias, source_slug in rows:
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            matched_from = f"merged:{source_slug}" if is_merge_alias else alias
            items.append(await h._serialize_destination(DestinationRepository(session), item, matched_from=matched_from))
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
        try:
            saved = await repository.set_status(item, is_active=payload.isActive)
        except DestinationReactivationError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "missingInputs": ["isActive"]}) from exc
        await session.commit()
        return await h._serialize_destination(repository, saved)


@router.post("/{destination_id}/merge")
async def merge_destination(destination_id: str, payload: DestinationMergeRequest, principal: Principal = Depends(require_quote_admin)):
    h = _get_helpers()
    async with h._get_db_session_factory()() as session:
        merged = await h._merge_destination(session, destination_id, payload.targetId, actor_email=principal.email)
        await session.commit()
        return await h._serialize_destination(DestinationRepository(session), merged)

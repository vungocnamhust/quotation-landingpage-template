"""Reusable FastAPI dependencies for V2 routes.

The aliases keep endpoint signatures explicit while preventing each router
from opening sessions or reimplementing authentication policy.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal, require_editor, require_editor_or_service, require_quote_admin
from db.session import get_db, get_session_factory
from repositories import BrandRepository, QuotationRepository
from repositories.travel_designer_repository import TravelDesignerRepository

V2_RENDERER_NAME = "quote-generator"
_session_factory_provider: Callable[[], object] = get_session_factory


def configure_session_factory_provider(provider: Callable[[], object]) -> None:
    """Bind dependencies to the ASGI composition root's session factory.

    Tests and deployments can replace that factory without API policy reaching
    back into ``main`` or constructing a second database engine.
    """
    global _session_factory_provider
    _session_factory_provider = provider


def _session_factory():
    return _session_factory_provider()

DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
EditorPrincipalDep = Annotated[Principal, Depends(require_editor)]
EditorOrServicePrincipalDep = Annotated[Principal, Depends(require_editor_or_service)]
QuoteAdminPrincipalDep = Annotated[Principal, Depends(require_quote_admin)]


async def get_active_travel_designer(principal: EditorPrincipalDep):
    if not principal.email:
        raise HTTPException(status_code=403, detail="An active Travel Designer profile is required. Contact a DMC administrator.")
    async with _session_factory()() as session:
        profile = await TravelDesignerRepository(session).get_active_by_email(principal.email)
    if profile is None:
        raise HTTPException(status_code=403, detail="An active Travel Designer profile is required. Contact a DMC administrator.")
    return profile


import os


def _is_admin_principal(principal: Principal) -> bool:
    if principal.source == "local":
        return True
    configured_roles = {
        role.strip().lower()
        for role in os.getenv("QUOTE_ADMIN_ROLES", "quote_admin,admin,supervisor").split(",")
        if role.strip()
    }
    roles = {
        role.strip().lower()
        for role in (principal.role or "").split(",")
        if role.strip()
    }
    return bool(configured_roles.intersection(roles))


async def require_owned_v2_quotation(
    quotation_id: str,
    principal: EditorPrincipalDep,
):
    """Enforce V2 quotation access with multi-tier authorization policy."""
    async with _session_factory()() as session:
        quotation = await QuotationRepository(session).get_quotation_by_id(quotation_id)
        if quotation is None or quotation.template_name != V2_RENDERER_NAME:
            raise HTTPException(status_code=404, detail=f"Quotation '{quotation_id}' was not found.")

        # 1. Service token & internal gateway bypass
        if principal.is_service:
            return quotation

        # 2. Local development & Admin roles bypass
        if _is_admin_principal(principal):
            return quotation

        # 3. Unassigned quotation is accessible to authenticated staff
        if not quotation.designer_profile_id and not quotation.created_by_profile_id:
            return quotation

        # 4. Authenticated Travel Designer profile check
        designer = await TravelDesignerRepository(session).get_active_by_email(principal.email) if principal.email else None
        if designer is None:
            raise HTTPException(
                status_code=403,
                detail="An active Travel Designer profile is required to access this quotation. Contact your DMC administrator.",
            )

        # 5. Assigned designer OR original creator check
        if quotation.designer_profile_id == designer.id or quotation.created_by_profile_id == designer.id:
            return quotation

        # 6. Explicit 403 Forbidden for unauthorized users
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Quotation '{quotation_id}' is owned by designer '{quotation.designer_profile_id}'.",
        )


OwnedV2QuotationDep = Annotated[object, Depends(require_owned_v2_quotation)]


async def require_active_brand(brand_id: str | None):
    if not brand_id:
        raise HTTPException(status_code=422, detail={"message": "brand_id is required."})
    async with _session_factory()() as session:
        brand = await BrandRepository(session).get_active(brand_id)
    if brand is None:
        raise HTTPException(status_code=422, detail={"message": "Brand is unavailable for V2.", "missingInputs": ["brand_id"]})
    return brand

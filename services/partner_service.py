from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.partner import PartnerProfile
from repositories.partner_repository import PartnerRepository
from schemas.v2.partner import (
    PartnerProfileCreateSchema,
    PartnerProfileResponseSchema,
    PartnerProfileUpdateSchema,
)


class PartnerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PartnerRepository(session)

    async def list_partners(
        self,
        *,
        active: Literal["true", "false", "all"] = "true",
        search: str = "",
        limit: int = 100,
    ) -> tuple[list[PartnerProfileResponseSchema], int]:
        active_only = {"true": True, "false": False, "all": None}[active]
        partners = await self.repository.list_partners(
            active_only=active_only,
            search=search,
            limit=limit,
        )
        items = [PartnerProfileResponseSchema.model_validate(p) for p in partners]
        return items, len(items)

    async def get_partner(self, partner_id: str) -> PartnerProfileResponseSchema | None:
        partner = await self.repository.get_partner(partner_id)
        if partner is None:
            return None
        return PartnerProfileResponseSchema.model_validate(partner)

    async def create_partner(self, payload: PartnerProfileCreateSchema) -> PartnerProfileResponseSchema:
        existing = await self.repository.get_by_email(payload.email)
        if existing:
            raise ValueError(f"A partner with email '{payload.email}' already exists.")

        partner_id = f"ptn_{uuid.uuid4().hex[:12]}"
        partner = await self.repository.create_partner(
            partner_id=partner_id,
            company_name=payload.company_name,
            contact_name=payload.contact_name,
            email=payload.email,
            phone=payload.phone,
            market=payload.market,
            tier=payload.tier,
            default_commission_rate=payload.default_commission_rate,
            preferred_currency=payload.preferred_currency,
            notes=payload.notes,
        )
        return PartnerProfileResponseSchema.model_validate(partner)

    async def update_partner(
        self, partner_id: str, payload: PartnerProfileUpdateSchema
    ) -> PartnerProfileResponseSchema | None:
        partner = await self.repository.get_partner(partner_id)
        if partner is None:
            return None

        if payload.email and payload.email.strip().lower() != partner.email:
            existing = await self.repository.get_by_email(payload.email)
            if existing and existing.id != partner_id:
                raise ValueError(f"A partner with email '{payload.email}' already exists.")

        updated = await self.repository.update_partner(
            partner,
            company_name=payload.company_name,
            contact_name=payload.contact_name,
            email=payload.email,
            phone=payload.phone,
            market=payload.market,
            tier=payload.tier,
            default_commission_rate=payload.default_commission_rate,
            preferred_currency=payload.preferred_currency,
            notes=payload.notes,
            is_active=payload.is_active,
        )
        return PartnerProfileResponseSchema.model_validate(updated)

    async def set_status(self, partner_id: str, *, is_active: bool) -> PartnerProfileResponseSchema | None:
        partner = await self.repository.get_partner(partner_id)
        if partner is None:
            return None
        updated = await self.repository.set_status(partner, is_active=is_active)
        return PartnerProfileResponseSchema.model_validate(updated)

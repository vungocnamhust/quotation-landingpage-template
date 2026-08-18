from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.partner import PartnerProfile


def normalize_partner_email(email: str) -> str:
    return (email or "").strip().lower()


class PartnerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_partners(
        self,
        *,
        active_only: bool | None = True,
        search: str = "",
        limit: int = 100,
    ) -> list[PartnerProfile]:
        stmt = select(PartnerProfile).order_by(PartnerProfile.company_name.asc(), PartnerProfile.contact_name.asc())
        if active_only is True:
            stmt = stmt.where(PartnerProfile.is_active.is_(True))
        elif active_only is False:
            stmt = stmt.where(PartnerProfile.is_active.is_(False))
        term = (search or "").strip()
        if term:
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(
                    PartnerProfile.company_name.ilike(pattern),
                    PartnerProfile.contact_name.ilike(pattern),
                    PartnerProfile.email.ilike(pattern),
                )
            )
        stmt = stmt.limit(max(1, min(limit, 200)))
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_partner(self, partner_id: str) -> PartnerProfile | None:
        return await self.session.get(PartnerProfile, partner_id)

    async def get_by_email(self, email: str) -> PartnerProfile | None:
        normalized = normalize_partner_email(email)
        if not normalized:
            return None
        return await self.session.scalar(
            select(PartnerProfile).where(PartnerProfile.email == normalized)
        )

    async def create_partner(
        self,
        *,
        partner_id: str,
        company_name: str,
        contact_name: str,
        email: str,
        phone: str = "",
        market: str | None = None,
        tier: str | None = "Standard",
        default_commission_rate: float = 10.0,
        preferred_currency: str = "USD",
        notes: str | None = None,
    ) -> PartnerProfile:
        now = datetime.now(timezone.utc)
        partner = PartnerProfile(
            id=partner_id,
            company_name=company_name.strip(),
            contact_name=contact_name.strip(),
            email=normalize_partner_email(email),
            phone=(phone or "").strip(),
            market=(market or "").strip() or None,
            tier=(tier or "Standard").strip(),
            default_commission_rate=default_commission_rate,
            preferred_currency=(preferred_currency or "USD").strip().upper(),
            notes=(notes or "").strip() or None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(partner)
        await self.session.flush()
        return partner

    async def update_partner(
        self,
        partner: PartnerProfile,
        *,
        company_name: str | None = None,
        contact_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        market: str | None = None,
        tier: str | None = None,
        default_commission_rate: float | None = None,
        preferred_currency: str | None = None,
        notes: str | None = None,
        is_active: bool | None = None,
    ) -> PartnerProfile:
        if company_name is not None:
            partner.company_name = company_name.strip()
        if contact_name is not None:
            partner.contact_name = contact_name.strip()
        if email is not None:
            partner.email = normalize_partner_email(email)
        if phone is not None:
            partner.phone = phone.strip()
        if market is not None:
            partner.market = market.strip() or None
        if tier is not None:
            partner.tier = tier.strip()
        if default_commission_rate is not None:
            partner.default_commission_rate = default_commission_rate
        if preferred_currency is not None:
            partner.preferred_currency = preferred_currency.strip().upper()
        if notes is not None:
            partner.notes = notes.strip() or None
        if is_active is not None:
            partner.is_active = is_active
        partner.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return partner

    async def set_status(self, partner: PartnerProfile, *, is_active: bool) -> PartnerProfile:
        partner.is_active = is_active
        partner.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return partner

from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.quote_request import QuoteRequest, QuoteRequestRevision


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:16]}"


class QuoteRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_request(
        self,
        *,
        role: str,
        customer_name: str,
        email: str,
        phone: str | None = None,
        company_name: str | None = None,
        market: str | None = None,
        preferred_contact: str | None = None,
        destinations: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        raw_dates_text: str | None = None,
        adults: int | None = 2,
        children: int | None = 0,
        kid_ages: list[int] | None = None,
        children_details: str | None = None,
        travel_style: str | None = None,
        special_requirements: str | None = None,
        payload_json: dict[str, Any] | None = None,
        created_by_profile_id: str | None = None,
        partner_id: str | None = None,
        request_id: str | None = None,
    ) -> QuoteRequest:
        rid = request_id or generate_request_id()
        req = QuoteRequest(
            id=rid,
            role=role,
            status="new",
            current_revision=1,
            customer_name=customer_name,
            email=email,
            phone=phone,
            company_name=company_name,
            market=market,
            preferred_contact=preferred_contact,
            destinations=destinations or [],
            start_date=start_date,
            end_date=end_date,
            raw_dates_text=raw_dates_text,
            adults=adults if adults is not None else 2,
            children=children if children is not None else 0,
            kid_ages=kid_ages or [],
            children_details=children_details,
            travel_style=travel_style,
            special_requirements=special_requirements,
            payload_json=payload_json or {},
            created_by_profile_id=created_by_profile_id,
            partner_id=partner_id,
        )
        self.session.add(req)
        await self.session.flush()

        # Create initial revision 1
        await self.create_revision(
            request_id=req.id,
            revision=1,
            role=role,
            customer_name=customer_name,
            email=email,
            phone=phone,
            company_name=company_name,
            market=market,
            preferred_contact=preferred_contact,
            destinations=destinations or [],
            start_date=start_date,
            end_date=end_date,
            raw_dates_text=raw_dates_text,
            adults=adults if adults is not None else 2,
            children=children if children is not None else 0,
            kid_ages=kid_ages or [],
            children_details=children_details,
            travel_style=travel_style,
            special_requirements=special_requirements,
            payload_json=payload_json or {},
            change_summary="Initial intake submission",
            change_source="initial_intake",
            created_by_profile_id=created_by_profile_id,
        )

        return req

    async def create_revision(
        self,
        *,
        request_id: str,
        revision: int,
        role: str,
        customer_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        company_name: str | None = None,
        market: str | None = None,
        preferred_contact: str | None = None,
        destinations: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        raw_dates_text: str | None = None,
        adults: int | None = 2,
        children: int | None = 0,
        kid_ages: list[int] | None = None,
        children_details: str | None = None,
        travel_style: str | None = None,
        special_requirements: str | None = None,
        payload_json: dict[str, Any] | None = None,
        change_summary: str | None = None,
        change_source: str = "manual_edit",
        created_by_profile_id: str | None = None,
    ) -> QuoteRequestRevision:
        rev = QuoteRequestRevision(
            request_id=request_id,
            revision=revision,
            role=role,
            customer_name=customer_name,
            email=email,
            phone=phone,
            company_name=company_name,
            market=market,
            preferred_contact=preferred_contact,
            destinations=destinations or [],
            start_date=start_date,
            end_date=end_date,
            raw_dates_text=raw_dates_text,
            adults=adults if adults is not None else 2,
            children=children if children is not None else 0,
            kid_ages=kid_ages or [],
            children_details=children_details,
            travel_style=travel_style,
            special_requirements=special_requirements,
            payload_json=payload_json or {},
            change_summary=change_summary,
            change_source=change_source,
            created_by_profile_id=created_by_profile_id,
        )
        self.session.add(rev)
        await self.session.flush()
        return rev

    async def get_by_id(self, request_id: str) -> QuoteRequest | None:
        return await self.session.get(QuoteRequest, request_id)

    async def get_revisions_by_request_id(self, request_id: str) -> list[QuoteRequestRevision]:
        stmt = (
            select(QuoteRequestRevision)
            .where(QuoteRequestRevision.request_id == request_id)
            .order_by(QuoteRequestRevision.revision.desc())
        )
        res = await self.session.scalars(stmt)
        return list(res.all())

    async def get_revision_by_number(self, request_id: str, revision: int) -> QuoteRequestRevision | None:
        stmt = (
            select(QuoteRequestRevision)
            .where(
                QuoteRequestRevision.request_id == request_id,
                QuoteRequestRevision.revision == revision,
            )
        )
        return await self.session.scalar(stmt)

    async def save_edited_request(
        self,
        req: QuoteRequest,
        *,
        role: str,
        customer_name: str,
        email: str,
        phone: str | None = None,
        company_name: str | None = None,
        market: str | None = None,
        preferred_contact: str | None = None,
        destinations: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        raw_dates_text: str | None = None,
        adults: int | None = 2,
        children: int | None = 0,
        kid_ages: list[int] | None = None,
        children_details: str | None = None,
        travel_style: str | None = None,
        special_requirements: str | None = None,
        payload_json: dict[str, Any] | None = None,
        partner_id: str | None = None,
        updated_by_profile_id: str | None = None,
        change_summary: str | None = None,
        change_source: str = "manual_edit",
    ) -> tuple[QuoteRequest, QuoteRequestRevision]:
        next_revision = (req.current_revision or 1) + 1
        req.current_revision = next_revision
        req.role = role
        req.customer_name = customer_name
        req.email = email
        req.phone = phone
        req.company_name = company_name
        req.market = market
        req.preferred_contact = preferred_contact
        req.destinations = destinations or []
        req.start_date = start_date
        req.end_date = end_date
        req.raw_dates_text = raw_dates_text
        req.adults = adults if adults is not None else 2
        req.children = children if children is not None else 0
        req.kid_ages = kid_ages or []
        req.children_details = children_details
        req.travel_style = travel_style
        req.special_requirements = special_requirements
        req.payload_json = payload_json or {}
        req.partner_id = partner_id
        req.updated_by_profile_id = updated_by_profile_id

        rev = await self.create_revision(
            request_id=req.id,
            revision=next_revision,
            role=role,
            customer_name=customer_name,
            email=email,
            phone=phone,
            company_name=company_name,
            market=market,
            preferred_contact=preferred_contact,
            destinations=destinations or [],
            start_date=start_date,
            end_date=end_date,
            raw_dates_text=raw_dates_text,
            adults=adults if adults is not None else 2,
            children=children if children is not None else 0,
            kid_ages=kid_ages or [],
            children_details=children_details,
            travel_style=travel_style,
            special_requirements=special_requirements,
            payload_json=payload_json or {},
            change_summary=change_summary,
            change_source=change_source,
            created_by_profile_id=updated_by_profile_id,
        )

        await self.session.flush()
        return req, rev

    async def list_requests(
        self,
        *,
        search: str = "",
        role: str | None = None,
        status: str | None = None,
        limit: int = 24,
        offset: int = 0,
    ) -> tuple[list[QuoteRequest], int]:
        stmt = select(QuoteRequest)
        count_stmt = select(func.count(QuoteRequest.id))

        if role:
            stmt = stmt.where(QuoteRequest.role == role)
            count_stmt = count_stmt.where(QuoteRequest.role == role)

        if status:
            stmt = stmt.where(QuoteRequest.status == status)
            count_stmt = count_stmt.where(QuoteRequest.status == status)

        term = (search or "").strip()
        if term:
            pattern = f"%{term}%"
            filter_cond = or_(
                QuoteRequest.id.ilike(pattern),
                QuoteRequest.customer_name.ilike(pattern),
                QuoteRequest.email.ilike(pattern),
                QuoteRequest.company_name.ilike(pattern),
                QuoteRequest.market.ilike(pattern),
                QuoteRequest.travel_style.ilike(pattern),
            )
            stmt = stmt.where(filter_cond)
            count_stmt = count_stmt.where(filter_cond)

        stmt = stmt.order_by(QuoteRequest.created_at.desc()).offset(offset).limit(max(1, min(limit, 100)))

        total_result = await self.session.scalar(count_stmt)
        total = total_result or 0

        items_result = await self.session.scalars(stmt)
        items = list(items_result.all())

        return items, total

    async def update_status(
        self,
        request_id: str,
        status: str,
        linked_quotation_id: str | None = None,
    ) -> QuoteRequest | None:
        req = await self.get_by_id(request_id)
        if not req:
            return None
        req.status = status
        if linked_quotation_id:
            req.linked_quotation_id = linked_quotation_id
        await self.session.flush()
        return req


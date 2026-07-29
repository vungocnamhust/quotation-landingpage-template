from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.publication import QuotationPublication
from db.models.quotation import Quotation


class PublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_publication(
        self,
        *,
        quotation_id: str,
        version: int,
        lang: str,
        html_r2_key: str,
        pdf_r2_key: str | None = None,
        published_url: str | None = None,
        pdf_url: str | None = None,
    ) -> QuotationPublication:
        quotation = await self.session.get(Quotation, quotation_id)
        if quotation is None:
            raise ValueError(f"Quotation {quotation_id} not found")

        publication = QuotationPublication(
            quotation_id=quotation_id,
            version=version,
            lang=lang,
            html_r2_key=html_r2_key,
            pdf_r2_key=pdf_r2_key,
            published_url=published_url,
            pdf_url=pdf_url,
        )
        self.session.add(publication)
        quotation.status = "published"
        quotation.current_version = max(quotation.current_version, version)
        await self.session.flush()
        return publication

    async def list_publications(
        self,
        quotation_id: str,
        *,
        lang: str | None = None,
        limit: int = 50,
    ) -> list[QuotationPublication]:
        stmt: Select[tuple[QuotationPublication]] = (
            select(QuotationPublication)
            .where(QuotationPublication.quotation_id == quotation_id)
            .order_by(QuotationPublication.version.desc(), QuotationPublication.created_at.desc())
            .limit(limit)
        )
        if lang:
            stmt = stmt.where(QuotationPublication.lang == lang)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_publication(
        self,
        *,
        quotation_id: str,
        version: int,
        lang: str,
    ) -> QuotationPublication | None:
        stmt = (
            select(QuotationPublication)
            .where(QuotationPublication.quotation_id == quotation_id)
            .where(QuotationPublication.version == version)
            .where(QuotationPublication.lang == lang)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

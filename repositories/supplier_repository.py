from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.rules.text_normalize import normalize_name
from db.models.supplier import Supplier

DEFAULT_TENANT_ID = "capella"


def _ilike_pattern(term: str) -> str:
    """Escapes ILIKE wildcard metacharacters so a literal ``%``/``_`` in a search
    term cannot expand into an unintended wildcard match."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class SupplierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        active_only: bool | None = True,
        search: str = "",
        supplier_type: str | None = None,
        destination_id: str | None = None,
        limit: int = 100,
    ) -> tuple[list[Supplier], int]:
        stmt = select(Supplier).where(Supplier.tenant_id == tenant_id)
        if active_only is True:
            stmt = stmt.where(Supplier.is_active.is_(True))
        elif active_only is False:
            stmt = stmt.where(Supplier.is_active.is_(False))
        if supplier_type:
            stmt = stmt.where(Supplier.supplier_type == supplier_type)
        if destination_id:
            stmt = stmt.where(Supplier.destination_id == destination_id)
        term = (search or "").strip()
        if term:
            # name_normalized/title-style columns store diacritic-stripped text, so the
            # search term must go through the same normalizer before ILIKE, or a staff
            # member typing accented Vietnamese gets zero results (Track 1 audit H5).
            normalized_pattern = _ilike_pattern(normalize_name(term))
            raw_pattern = _ilike_pattern(term)
            stmt = stmt.where(
                or_(
                    Supplier.name_normalized.ilike(normalized_pattern, escape="\\"),
                    Supplier.legal_name.ilike(raw_pattern, escape="\\"),
                    Supplier.contact_json["person"].as_string().ilike(raw_pattern, escape="\\"),
                )
            )

        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))

        stmt = stmt.order_by(Supplier.name.asc()).limit(max(1, min(limit, 200)))
        result = await self.session.scalars(stmt)
        items = list(result.all())
        return items, int(total or 0)

    async def get_by_id(self, supplier_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> Supplier | None:
        supplier = await self.session.get(Supplier, supplier_id)
        if supplier is None or supplier.tenant_id != tenant_id:
            return None
        return supplier

    async def get_by_normalized_name(self, name_normalized: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> Supplier | None:
        return await self.session.scalar(
            select(Supplier).where(
                Supplier.tenant_id == tenant_id,
                Supplier.name_normalized == name_normalized,
            )
        )

    async def insert(self, *, supplier_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]) -> Supplier:
        now = datetime.now(timezone.utc)
        supplier = Supplier(
            id=supplier_id,
            tenant_id=tenant_id,
            is_active=True,
            created_at=now,
            updated_at=now,
            **values,
        )
        self.session.add(supplier)
        await self.session.flush()
        return supplier

    async def update(self, supplier: Supplier, *, values: dict[str, Any]) -> Supplier:
        for field, value in values.items():
            setattr(supplier, field, value)
        supplier.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return supplier

    async def set_status(self, supplier: Supplier, *, is_active: bool, updated_by: str | None) -> Supplier:
        supplier.is_active = is_active
        supplier.updated_by = updated_by
        supplier.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return supplier

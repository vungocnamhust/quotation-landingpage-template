from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.rules.text_normalize import normalize_name
from db.models.product import Product

DEFAULT_TENANT_ID = "capella"


def _ilike_pattern(term: str) -> str:
    """Escapes ILIKE wildcard metacharacters so a literal ``%``/``_`` in a search
    term cannot expand into an unintended wildcard match."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        active_only: bool | None = True,
        category: str | None = None,
        destination_id: str | None = None,
        supplier_id: str | None = None,
        property_id: str | None = None,
        search: str = "",
        limit: int = 100,
    ) -> tuple[list[Product], int]:
        stmt = select(Product).where(Product.tenant_id == tenant_id)
        if active_only is True:
            stmt = stmt.where(Product.is_active.is_(True))
        elif active_only is False:
            stmt = stmt.where(Product.is_active.is_(False))
        if category:
            stmt = stmt.where(Product.category == category)
        if destination_id:
            stmt = stmt.where(Product.destination_id == destination_id)
        if supplier_id:
            stmt = stmt.where(Product.supplier_id == supplier_id)
        if property_id:
            stmt = stmt.where(Product.property_id == property_id)
        term = (search or "").strip()
        if term:
            # title_normalized stores diacritic-stripped text, so the search term must
            # go through the same normalizer before ILIKE (Track 1 audit H5).
            pattern = _ilike_pattern(normalize_name(term))
            stmt = stmt.where(Product.title_normalized.ilike(pattern, escape="\\"))

        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))

        stmt = stmt.order_by(Product.title.asc()).limit(max(1, min(limit, 200)))
        result = await self.session.scalars(stmt)
        items = list(result.all())
        return items, int(total or 0)

    async def get_by_id(self, product_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> Product | None:
        product = await self.session.get(Product, product_id)
        if product is None or product.tenant_id != tenant_id:
            return None
        return product

    async def get_by_ids(self, product_ids: set[str], *, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, Product]:
        if not product_ids:
            return {}
        result = await self.session.scalars(
            select(Product).where(Product.id.in_(product_ids), Product.tenant_id == tenant_id)
        )
        return {product.id: product for product in result}

    async def find_dedupe_conflict(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        destination_id: str,
        category: str,
        title_normalized: str,
        supplier_id: str | None,
        origin_destination_id: str | None = None,
        exclude_id: str | None = None,
    ) -> Product | None:
        stmt = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.destination_id == destination_id,
            Product.category == category,
            Product.title_normalized == title_normalized,
            Product.supplier_id.is_(None) if supplier_id is None else Product.supplier_id == supplier_id,
            Product.origin_destination_id.is_(None)
            if origin_destination_id is None
            else Product.origin_destination_id == origin_destination_id,
        )
        if exclude_id:
            stmt = stmt.where(Product.id != exclude_id)
        return await self.session.scalar(stmt)

    async def insert(self, *, product_id: str, tenant_id: str = DEFAULT_TENANT_ID, values: dict[str, Any]) -> Product:
        now = datetime.now(timezone.utc)
        product = Product(
            id=product_id,
            tenant_id=tenant_id,
            is_active=True,
            created_at=now,
            updated_at=now,
            **values,
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def update(self, product: Product, *, values: dict[str, Any]) -> Product:
        for field, value in values.items():
            setattr(product, field, value)
        product.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return product

    async def set_status(self, product: Product, *, is_active: bool, updated_by: str | None) -> Product:
        product.is_active = is_active
        product.updated_by = updated_by
        product.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return product

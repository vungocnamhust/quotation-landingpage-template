from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.product import Product

DEFAULT_TENANT_ID = "capella"


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
        stmt = select(Product).where(Product.tenant_id == tenant_id).order_by(Product.title.asc())
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
            stmt = stmt.where(Product.title_normalized.ilike(f"%{term}%"))
        stmt = stmt.limit(max(1, min(limit, 200)))
        result = await self.session.scalars(stmt)
        items = list(result.all())
        return items, len(items)

    async def get_by_id(self, product_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> Product | None:
        product = await self.session.get(Product, product_id)
        if product is None or product.tenant_id != tenant_id:
            return None
        return product

    async def find_dedupe_conflict(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        destination_id: str,
        category: str,
        title_normalized: str,
        supplier_id: str | None,
        exclude_id: str | None = None,
    ) -> Product | None:
        stmt = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.destination_id == destination_id,
            Product.category == category,
            Product.title_normalized == title_normalized,
            Product.supplier_id.is_(None) if supplier_id is None else Product.supplier_id == supplier_id,
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

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base
from db.types import JSON_VARIANT


class Product(Base):
    """A sellable service variant of a supplier at a destination (15.2).

    Product == Tourplan Option (Location + Category + Supplier + variant).
    Contains no amount/price/currency column by design (R2: Product != Rate,
    pricing is 15.3). See 15.2-product-catalog.md.
    """

    __tablename__ = "products"
    __table_args__ = (
        Index(
            "uq_products_tenant_destination_category_title_supplier",
            "tenant_id",
            "destination_id",
            "category",
            "title_normalized",
            text("coalesce(supplier_id, '')"),
            unique=True,
        ),
        Index("ix_products_tenant_destination_category_active", "tenant_id", "destination_id", "category", "is_active"),
        Index("ix_products_supplier_id", "supplier_id"),
        Index("ix_products_property_id", "property_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="capella", server_default="capella", index=True)

    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True)
    property_id: Mapped[str | None] = mapped_column(ForeignKey("accommodation_profiles.id", ondelete="RESTRICT"), nullable=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destination_catalog.id", ondelete="RESTRICT"), nullable=False)

    category: Mapped[str] = mapped_column(String(24), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(48), nullable=True)
    subcategory_note: Mapped[str | None] = mapped_column(String(120), nullable=True)

    supplier_product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_normalized: Mapped[str] = mapped_column(String(255), nullable=False)

    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    time_basis: Mapped[str] = mapped_column(String(16), nullable=False)

    default_min_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_max_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category_attributes: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict, server_default="{}")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

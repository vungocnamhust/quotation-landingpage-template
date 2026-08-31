"""Read-only dependency bag for AI Platform agents (15.8 §1.1, bootstrap for 15.7).

``CatalogReadOnlyDeps`` is the ``deps`` object passed to every ``pydantic_ai.Agent`` built
via ``runtime.build_agent``. It carries only read repositories plus a ``tenant_id`` supplied
by the caller (never by the LLM) and an ``AllowlistRecorder`` to log every id a tool hands
back. It has NO method that writes to the database — that is a structural guarantee, asserted
directly by ``tests/test_ai_platform_toolset.py`` (no attribute name containing "insert",
"update", "delete", "create", or "commit" resolves to anything but a read-only repository
method).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.destination_repository import DestinationRepository
from repositories.product_repository import ProductRepository
from repositories.rate_repository import RateRepository
from repositories.supplier_repository import SupplierRepository
from services.ai_platform.guardrails import AllowlistRecorder, RunBudget


@dataclass
class CatalogReadOnlyDeps:
    session: AsyncSession
    tenant_id: str
    allowlist: AllowlistRecorder
    budget: RunBudget

    @property
    def supplier_repository(self) -> SupplierRepository:
        return SupplierRepository(self.session)

    @property
    def product_repository(self) -> ProductRepository:
        return ProductRepository(self.session)

    @property
    def rate_repository(self) -> RateRepository:
        return RateRepository(self.session)

    @property
    def destination_repository(self) -> DestinationRepository:
        return DestinationRepository(self.session)

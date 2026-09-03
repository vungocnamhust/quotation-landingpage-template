"""Read-only dependency bag for AI Platform agents (15.8 §1.1, bootstrap for 15.7).

``CatalogReadOnlyDeps`` is the ``deps`` object passed to every ``pydantic_ai.Agent`` built
via ``runtime.build_agent``. It carries only read-only facades plus a ``tenant_id`` supplied
by the caller (never by the LLM) and an ``AllowlistRecorder`` to log every id a tool hands
back.

Read-only "by construction, not by convention" (Track 4 audit H7): the raw ``AsyncSession``
is private (``_session``, never a public attribute) and every repository is wrapped in a
facade that exposes ONLY the handful of query methods the catalog toolset actually calls —
``list``/``list_by_product``/``effective_destination_id``. A facade has no ``create``,
``update``, ``delete``, or ``commit`` method to call by mistake, and no access to ``.session``
to reach around it — unlike the underlying repositories, which are full read/write classes.
This is asserted recursively (one attribute-hop deep) by
``tests/test_ai_platform_toolset.py::test_deps_has_no_write_method``.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.destination_repository import DestinationRepository
from repositories.product_repository import ProductRepository
from repositories.rate_repository import RateRepository
from repositories.supplier_repository import SupplierRepository
from services.ai_platform.guardrails import AllowlistRecorder, RunBudget


class _ReadOnlySupplierFacade:
    __slots__ = ("_repository",)

    def __init__(self, repository: SupplierRepository) -> None:
        self._repository = repository

    async def list(self, **kwargs):
        return await self._repository.list(**kwargs)


class _ReadOnlyProductFacade:
    __slots__ = ("_repository",)

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def list(self, **kwargs):
        return await self._repository.list(**kwargs)


class _ReadOnlyRateFacade:
    __slots__ = ("_repository",)

    def __init__(self, repository: RateRepository) -> None:
        self._repository = repository

    async def list_by_product(self, product_id: str, **kwargs):
        return await self._repository.list_by_product(product_id, **kwargs)


class _ReadOnlyDestinationFacade:
    __slots__ = ("_repository",)

    def __init__(self, repository: DestinationRepository) -> None:
        self._repository = repository

    async def effective_destination_id(self, destination_id: str, **kwargs) -> str:
        return await self._repository.effective_destination_id(destination_id, **kwargs)


class CatalogReadOnlyDeps:
    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: str,
        allowlist: AllowlistRecorder,
        budget: RunBudget,
    ) -> None:
        self._session = session
        self.tenant_id = tenant_id
        self.allowlist = allowlist
        self.budget = budget

    @property
    def supplier_repository(self) -> _ReadOnlySupplierFacade:
        return _ReadOnlySupplierFacade(SupplierRepository(self._session))

    @property
    def product_repository(self) -> _ReadOnlyProductFacade:
        return _ReadOnlyProductFacade(ProductRepository(self._session))

    @property
    def rate_repository(self) -> _ReadOnlyRateFacade:
        return _ReadOnlyRateFacade(RateRepository(self._session))

    @property
    def destination_repository(self) -> _ReadOnlyDestinationFacade:
        return _ReadOnlyDestinationFacade(DestinationRepository(self._session))

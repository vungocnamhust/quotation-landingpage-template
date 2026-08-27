from __future__ import annotations

import re
import unicodedata
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id
from core.rules.pricing_rules import SUPPORTED_CURRENCIES
from repositories.supplier_repository import SupplierRepository
from schemas.v2.supplier import SupplierCreateSchema, SupplierResponseSchema, SupplierUpdateSchema

_WHITESPACE_RE = re.compile(r"\s+")

ID_PREFIX = "sup"


def normalize_supplier_name(name: str) -> str:
    """lower + strip diacritics + collapse whitespace (mirrors 15.2 dedupe)."""
    decomposed = unicodedata.normalize("NFD", name or "")
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    collapsed = _WHITESPACE_RE.sub(" ", without_marks).strip().lower()
    return collapsed


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SupplierRepository(session)

    async def list_suppliers(
        self,
        *,
        active: Literal["true", "false", "all"] = "true",
        search: str = "",
        supplier_type: str | None = None,
        destination_id: str | None = None,
        limit: int = 100,
    ) -> tuple[list[SupplierResponseSchema], int]:
        active_only = {"true": True, "false": False, "all": None}[active]
        suppliers, total = await self.repository.list(
            active_only=active_only,
            search=search,
            supplier_type=supplier_type,
            destination_id=destination_id,
            limit=limit,
        )
        items = [SupplierResponseSchema.model_validate(s) for s in suppliers]
        return items, total

    async def get_supplier(self, supplier_id: str) -> SupplierResponseSchema | None:
        supplier = await self.repository.get_by_id(supplier_id)
        if supplier is None:
            return None
        return SupplierResponseSchema.model_validate(supplier)

    async def create_supplier(self, payload: SupplierCreateSchema, *, actor: ActorRef) -> SupplierResponseSchema:
        self._validate_currency(payload.default_currency)
        name_normalized = normalize_supplier_name(payload.name)
        existing = await self.repository.get_by_normalized_name(name_normalized)
        if existing:
            raise ValueError(f"A supplier named '{payload.name}' already exists.")

        supplier_id = generate_id(ID_PREFIX)
        values = self._payload_to_values(payload)
        values["name_normalized"] = name_normalized
        values["created_by"] = actor.serialize()
        values["updated_by"] = actor.serialize()
        supplier = await self.repository.insert(supplier_id=supplier_id, values=values)
        return SupplierResponseSchema.model_validate(supplier)

    async def update_supplier(
        self, supplier_id: str, payload: SupplierUpdateSchema, *, actor: ActorRef
    ) -> SupplierResponseSchema | None:
        supplier = await self.repository.get_by_id(supplier_id)
        if supplier is None:
            return None

        updates = payload.model_dump(exclude_unset=True)
        if "default_currency" in updates and updates["default_currency"] is not None:
            self._validate_currency(updates["default_currency"])

        if "name" in updates and updates["name"] is not None:
            name_normalized = normalize_supplier_name(updates["name"])
            if name_normalized != supplier.name_normalized:
                conflict = await self.repository.get_by_normalized_name(name_normalized)
                if conflict and conflict.id != supplier_id:
                    raise ValueError(f"A supplier named '{updates['name']}' already exists.")
            updates["name_normalized"] = name_normalized

        updates["updated_by"] = actor.serialize()
        updated = await self.repository.update(supplier, values=updates)
        return SupplierResponseSchema.model_validate(updated)

    async def set_status(self, supplier_id: str, *, is_active: bool, actor: ActorRef) -> SupplierResponseSchema | None:
        supplier = await self.repository.get_by_id(supplier_id)
        if supplier is None:
            return None
        updated = await self.repository.set_status(supplier, is_active=is_active, updated_by=actor.serialize())
        return SupplierResponseSchema.model_validate(updated)

    @staticmethod
    def _validate_currency(currency: str) -> None:
        if currency.upper() not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency '{currency}'.")

    @staticmethod
    def _payload_to_values(payload: SupplierCreateSchema) -> dict:
        values = payload.model_dump()
        values["default_currency"] = values["default_currency"].upper()
        values["contact_json"] = payload.contact_json.model_dump()
        values["payment_terms_json"] = payload.payment_terms_json.model_dump() if payload.payment_terms_json else None
        values["cancellation_policy_json"] = (
            payload.cancellation_policy_json.model_dump() if payload.cancellation_policy_json else None
        )
        values["child_policy_json"] = payload.child_policy_json.model_dump() if payload.child_policy_json else None
        values["name"] = payload.name.strip()
        return values

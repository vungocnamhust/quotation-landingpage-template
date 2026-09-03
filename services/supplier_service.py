from __future__ import annotations

from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id
from core.rules.pricing_rules import SUPPORTED_CURRENCIES
from core.rules.text_normalize import normalize_name
from repositories.destination_repository import DestinationRepository
from repositories.supplier_repository import SupplierRepository
from schemas.v2.supplier import SupplierCreateSchema, SupplierResponseSchema, SupplierUpdateSchema

ID_PREFIX = "sup"

# Single canonical normalizer (Track 1 audit H1): must remain the same object as
# services.product_service.normalize_product_title, not a copy.
normalize_supplier_name = normalize_name


class SupplierValidationError(ValueError):
    """Business-rule violation caught in the service layer (maps to 422)."""


class SupplierConflictError(ValueError):
    """Dedupe key collision (maps to 409)."""


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SupplierRepository(session)
        self.destination_repository = DestinationRepository(session)

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
        await self._validate_destination_exists(payload.destination_id)
        name_normalized = normalize_supplier_name(payload.name)
        existing = await self.repository.get_by_normalized_name(name_normalized)
        if existing:
            raise SupplierConflictError(f"A supplier named '{payload.name}' already exists.")

        supplier_id = generate_id(ID_PREFIX)
        values = self._payload_to_values(payload)
        values["name_normalized"] = name_normalized
        values["created_by"] = actor.serialize()
        values["updated_by"] = actor.serialize()
        try:
            async with self.session.begin_nested():
                supplier = await self.repository.insert(supplier_id=supplier_id, values=values)
        except IntegrityError as exc:
            raise SupplierConflictError(f"A supplier named '{payload.name}' already exists.") from exc
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

        if "destination_id" in updates:
            await self._validate_destination_exists(updates["destination_id"])

        if "name" in updates and updates["name"] is not None:
            name_normalized = normalize_supplier_name(updates["name"])
            if name_normalized != supplier.name_normalized:
                conflict = await self.repository.get_by_normalized_name(name_normalized)
                if conflict and conflict.id != supplier_id:
                    raise SupplierConflictError(f"A supplier named '{updates['name']}' already exists.")
            updates["name_normalized"] = name_normalized

        updates["updated_by"] = actor.serialize()
        try:
            async with self.session.begin_nested():
                updated = await self.repository.update(supplier, values=updates)
        except IntegrityError as exc:
            raise SupplierConflictError(f"A supplier named '{updates.get('name', supplier.name)}' already exists.") from exc
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
            raise SupplierValidationError(f"Unsupported currency '{currency}'.")

    async def _validate_destination_exists(self, destination_id: str | None, *, field: str = "destination_id") -> None:
        if destination_id is None:
            return
        destination = await self.destination_repository.get(destination_id)
        if destination is None:
            raise SupplierValidationError(f"{field} '{destination_id}' was not found.")
        if destination.merged_into_id is not None:
            raise SupplierValidationError(
                f"Destination '{destination_id}' has been merged into '{destination.merged_into_id}'."
            )
        if not destination.is_active:
            raise SupplierValidationError(f"Destination '{destination_id}' is inactive.")

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

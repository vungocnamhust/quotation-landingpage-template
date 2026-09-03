from __future__ import annotations

from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.kernel import ActorRef, generate_id
from core.rules.catalog_vocab import DEFAULT_CHARGE_UNIT_BY_CATEGORY, SUBCATEGORY_BY_CATEGORY
from core.rules.text_normalize import normalize_name
from repositories.accommodation_repository import AccommodationRepository
from repositories.destination_repository import DestinationRepository
from repositories.product_repository import ProductRepository
from repositories.supplier_repository import SupplierRepository
from schemas.v2.product import ProductCreateSchema, ProductResponseSchema, ProductUpdateSchema

ID_PREFIX = "prd"

_SENTINEL = object()


class ProductValidationError(ValueError):
    """Business-rule violation caught in the service layer (maps to 422)."""


class ProductConflictError(ValueError):
    """Dedupe key collision (maps to 409)."""


# Single canonical normalizer (Track 1 audit H1): must remain the same object as
# services.supplier_service.normalize_supplier_name, not a copy.
normalize_product_title = normalize_name


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProductRepository(session)
        self.accommodation_repository = AccommodationRepository(session)
        self.destination_repository = DestinationRepository(session)
        self.supplier_repository = SupplierRepository(session)

    async def list_products(
        self,
        *,
        active: Literal["true", "false", "all"] = "true",
        category: str | None = None,
        destination_id: str | None = None,
        supplier_id: str | None = None,
        property_id: str | None = None,
        search: str = "",
        limit: int = 100,
    ) -> tuple[list[ProductResponseSchema], int]:
        active_only = {"true": True, "false": False, "all": None}[active]
        products, total = await self.repository.list(
            active_only=active_only,
            category=category,
            destination_id=destination_id,
            supplier_id=supplier_id,
            property_id=property_id,
            search=search,
            limit=limit,
        )
        items = [ProductResponseSchema.model_validate(p) for p in products]
        return items, total

    async def get_product(self, product_id: str) -> ProductResponseSchema | None:
        product = await self.repository.get_by_id(product_id)
        if product is None:
            return None
        return ProductResponseSchema.model_validate(product)

    async def create_product(self, payload: ProductCreateSchema, *, actor: ActorRef) -> ProductResponseSchema:
        await self._validate_subcategory(payload.category, payload.subcategory, payload.subcategory_note)
        await self._validate_property(payload.category, payload.property_id, payload.destination_id)
        await self._validate_origin(payload.category, payload.origin_destination_id, payload.destination_id)
        await self._validate_destination_exists(payload.destination_id)
        await self._validate_destination_exists(payload.origin_destination_id, field="origin_destination_id")
        await self._validate_supplier_exists(payload.supplier_id)

        title_normalized = normalize_product_title(payload.title)
        conflict = await self.repository.find_dedupe_conflict(
            destination_id=payload.destination_id,
            category=payload.category,
            title_normalized=title_normalized,
            supplier_id=payload.supplier_id,
            origin_destination_id=payload.origin_destination_id,
        )
        if conflict:
            raise ProductConflictError(
                f"A product named '{payload.title}' already exists for this destination/category/supplier."
            )

        unit, time_basis = self._resolve_charge_unit(payload.category, payload.unit, payload.time_basis)

        values = payload.model_dump(exclude={"unit", "time_basis"})
        values["unit"] = unit
        values["time_basis"] = time_basis
        values["title"] = payload.title.strip()
        values["title_normalized"] = title_normalized
        values["created_by"] = actor.serialize()
        values["updated_by"] = actor.serialize()

        product_id = generate_id(ID_PREFIX)
        try:
            product = await self.repository.insert(product_id=product_id, values=values)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProductConflictError(
                f"A product named '{payload.title}' already exists for this destination/category/supplier."
            ) from exc
        return ProductResponseSchema.model_validate(product)

    async def update_product(
        self, product_id: str, payload: ProductUpdateSchema, *, actor: ActorRef
    ) -> ProductResponseSchema | None:
        product = await self.repository.get_by_id(product_id)
        if product is None:
            return None

        updates = payload.model_dump(exclude_unset=True)

        if "supplier_product_name" in updates and updates["supplier_product_name"] != product.supplier_product_name:
            raise ProductValidationError("supplier_product_name is immutable after creation.")

        category = updates.get("category", product.category)
        subcategory = updates.get("subcategory", product.subcategory)
        subcategory_note = updates.get("subcategory_note", _SENTINEL)
        if subcategory_note is _SENTINEL:
            subcategory_note = product.subcategory_note
        if "subcategory" in updates or "category" in updates or "subcategory_note" in updates:
            subcategory_note = await self._validate_subcategory(category, subcategory, subcategory_note)
            updates["subcategory_note"] = subcategory_note

        property_id = updates.get("property_id", product.property_id)
        destination_id = updates.get("destination_id", product.destination_id)
        if "property_id" in updates or "category" in updates or "destination_id" in updates:
            await self._validate_property(category, property_id, destination_id)

        origin_destination_id = updates.get("origin_destination_id", product.origin_destination_id)
        if "origin_destination_id" in updates or "category" in updates or "destination_id" in updates:
            await self._validate_origin(category, origin_destination_id, destination_id)

        if "destination_id" in updates:
            await self._validate_destination_exists(destination_id)
        if "origin_destination_id" in updates:
            await self._validate_destination_exists(origin_destination_id, field="origin_destination_id")
        if "supplier_id" in updates:
            await self._validate_supplier_exists(updates["supplier_id"])

        if "title" in updates and updates["title"] is not None:
            updates["title"] = updates["title"].strip()
            updates["title_normalized"] = normalize_product_title(updates["title"])

        needs_dedupe_check = any(
            field in updates
            for field in ("title", "category", "destination_id", "supplier_id", "origin_destination_id")
        )
        if needs_dedupe_check:
            title_normalized = updates.get("title_normalized", product.title_normalized)
            supplier_id = updates.get("supplier_id", product.supplier_id)
            conflict = await self.repository.find_dedupe_conflict(
                destination_id=destination_id,
                category=category,
                title_normalized=title_normalized,
                supplier_id=supplier_id,
                origin_destination_id=origin_destination_id,
                exclude_id=product_id,
            )
            if conflict:
                raise ProductConflictError("A product with this title/destination/category/supplier already exists.")

        updates["updated_by"] = actor.serialize()
        try:
            updated = await self.repository.update(product, values=updates)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProductConflictError("A product with this title/destination/category/supplier already exists.") from exc
        return ProductResponseSchema.model_validate(updated)

    async def set_status(self, product_id: str, *, is_active: bool, actor: ActorRef) -> ProductResponseSchema | None:
        product = await self.repository.get_by_id(product_id)
        if product is None:
            return None
        updated = await self.repository.set_status(product, is_active=is_active, updated_by=actor.serialize())
        return ProductResponseSchema.model_validate(updated)

    @staticmethod
    def _resolve_charge_unit(category: str, unit: str | None, time_basis: str | None) -> tuple[str, str]:
        default_unit, default_time_basis = DEFAULT_CHARGE_UNIT_BY_CATEGORY[category]
        return unit or default_unit, time_basis or default_time_basis

    @staticmethod
    async def _validate_subcategory(
        category: str, subcategory: str | None, subcategory_note: str | None
    ) -> str | None:
        """Validates the (subcategory, subcategory_note) pair on the *merged* state
        (existing row + payload), not the payload in isolation (Track 1 audit H6).

        Schema-level validation only ever sees the payload, so a partial PUT that
        changes only ``subcategory`` (away from an ``other_*`` value) without also
        clearing ``subcategory_note`` would otherwise leave a stale note bound to
        an invalid combination. Doing this check here, on the state that will
        actually be persisted, rejects that combination outright instead of
        silently saving it.
        """
        if subcategory is not None:
            allowed = SUBCATEGORY_BY_CATEGORY[category]
            if subcategory not in allowed:
                raise ProductValidationError(
                    f"'{subcategory}' is not a valid subcategory for category '{category}'. "
                    f"Valid options: {sorted(allowed)}"
                )
        if subcategory_note is not None and not (subcategory or "").startswith("other_"):
            raise ProductValidationError("subcategory_note is only meaningful when subcategory is an other_* value.")
        return subcategory_note

    @staticmethod
    async def _validate_origin(category: str, origin_destination_id: str | None, destination_id: str) -> None:
        if origin_destination_id is not None and category not in ("transportation", "flights"):
            raise ProductValidationError(
                "origin_destination_id may only be set when category is 'transportation' or 'flights'."
            )
        if origin_destination_id is not None and origin_destination_id == destination_id:
            raise ProductValidationError("origin_destination_id must differ from destination_id.")

    async def _validate_property(self, category: str, property_id: str | None, destination_id: str) -> None:
        if property_id is None:
            return
        if category != "accommodation":
            raise ProductValidationError("property_id may only be set when category == 'accommodation'.")
        profile = await self.accommodation_repository.get_profile(property_id)
        if profile is None:
            raise ProductValidationError(f"Accommodation profile '{property_id}' was not found.")
        if profile.destination_id != destination_id:
            raise ProductValidationError("property_id must belong to the same destination_id as the product.")

    async def _validate_destination_exists(self, destination_id: str | None, *, field: str = "destination_id") -> None:
        if destination_id is None:
            return
        destination = await self.destination_repository.get(destination_id)
        if destination is None:
            raise ProductValidationError(f"{field} '{destination_id}' was not found.")

    async def _validate_supplier_exists(self, supplier_id: str | None) -> None:
        if supplier_id is None:
            return
        supplier = await self.supplier_repository.get_by_id(supplier_id)
        if supplier is None:
            raise ProductValidationError(f"supplier_id '{supplier_id}' was not found.")

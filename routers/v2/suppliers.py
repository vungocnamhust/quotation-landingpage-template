"""V2 supplier catalog routes (creditor-side registry, mirrors partners)."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from api.dependencies import DbSessionDep, EditorPrincipalDep
from core.kernel import ActorRef
from schemas.v2.supplier import (
    SupplierCreateSchema,
    SupplierListResponseSchema,
    SupplierResponseSchema,
    SupplierUpdateSchema,
)
from services.supplier_service import SupplierService

router = APIRouter(prefix="/api/v2/suppliers", tags=["suppliers"])


def _actor_from_principal(principal: EditorPrincipalDep) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


@router.get("", response_model=SupplierListResponseSchema)
async def list_suppliers(
    session: DbSessionDep,
    active: Annotated[Literal["true", "false", "all"], Query(description="Filter by active status")] = "true",
    search: Annotated[str, Query(description="Search by name or legal name")] = "",
    supplier_type: Annotated[str | None, Query(description="Filter by supplier_type")] = None,
    destination_id: Annotated[str | None, Query(description="Filter by destination_id")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    principal: EditorPrincipalDep = None,
) -> SupplierListResponseSchema:
    service = SupplierService(session)
    items, total = await service.list_suppliers(
        active=active,
        search=search,
        supplier_type=supplier_type,
        destination_id=destination_id,
        limit=limit,
    )
    return SupplierListResponseSchema(items=items, total=total)


@router.post("", response_model=SupplierResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> SupplierResponseSchema:
    service = SupplierService(session)
    try:
        supplier = await service.create_supplier(payload, actor=_actor_from_principal(principal))
        await session.commit()
        return supplier
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.get("/{supplier_id}", response_model=SupplierResponseSchema)
async def get_supplier(
    supplier_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> SupplierResponseSchema:
    service = SupplierService(session)
    supplier = await service.get_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier was not found.")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponseSchema)
async def update_supplier(
    supplier_id: str,
    payload: SupplierUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> SupplierResponseSchema:
    service = SupplierService(session)
    try:
        supplier = await service.update_supplier(supplier_id, payload, actor=_actor_from_principal(principal))
        if supplier is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier was not found.")
        await session.commit()
        return supplier
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err


@router.patch("/{supplier_id}/status", response_model=SupplierResponseSchema)
async def set_supplier_status(
    supplier_id: str,
    payload: dict[str, bool],
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> SupplierResponseSchema:
    if "isActive" not in payload and "is_active" not in payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="isActive is required")
    is_active = bool(payload.get("isActive", payload.get("is_active", True)))

    service = SupplierService(session)
    supplier = await service.set_status(supplier_id, is_active=is_active, actor=_actor_from_principal(principal))
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier was not found.")
    await session.commit()
    return supplier

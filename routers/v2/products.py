"""V2 product catalog routes (15.2 — mirrors suppliers/partners)."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.dependencies import DbSessionDep, EditorPrincipalDep
from core.kernel import ActorRef
from schemas.v2.product import (
    ProductCreateSchema,
    ProductListResponseSchema,
    ProductResponseSchema,
    ProductUpdateSchema,
)
from services.product_service import ProductConflictError, ProductService, ProductValidationError

router = APIRouter(prefix="/api/v2/products", tags=["products"])


class ProductStatusUpdateSchema(BaseModel):
    is_active: bool = Field(alias="isActive")


def _actor_from_principal(principal: EditorPrincipalDep) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


@router.get("", response_model=ProductListResponseSchema)
async def list_products(
    session: DbSessionDep,
    active: Annotated[Literal["true", "false", "all"], Query(description="Filter by active status")] = "true",
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    destination_id: Annotated[str | None, Query(description="Filter by destination_id")] = None,
    supplier_id: Annotated[str | None, Query(description="Filter by supplier_id")] = None,
    property_id: Annotated[str | None, Query(description="Filter by property_id")] = None,
    search: Annotated[str, Query(description="Search by title_normalized")] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    principal: EditorPrincipalDep = None,
) -> ProductListResponseSchema:
    service = ProductService(session)
    items, total = await service.list_products(
        active=active,
        category=category,
        destination_id=destination_id,
        supplier_id=supplier_id,
        property_id=property_id,
        search=search,
        limit=limit,
    )
    return ProductListResponseSchema(items=items, total=total)


@router.post("", response_model=ProductResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> ProductResponseSchema:
    service = ProductService(session)
    try:
        product = await service.create_product(payload, actor=_actor_from_principal(principal))
        await session.commit()
        return product
    except ProductConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except ProductValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err


@router.get("/{product_id}", response_model=ProductResponseSchema)
async def get_product(
    product_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> ProductResponseSchema:
    service = ProductService(session)
    product = await service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product was not found.")
    return product


@router.put("/{product_id}", response_model=ProductResponseSchema)
async def update_product(
    product_id: str,
    payload: ProductUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> ProductResponseSchema:
    service = ProductService(session)
    try:
        product = await service.update_product(product_id, payload, actor=_actor_from_principal(principal))
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product was not found.")
        await session.commit()
        return product
    except ProductConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except ProductValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err


@router.patch("/{product_id}/status", response_model=ProductResponseSchema)
async def set_product_status(
    product_id: str,
    payload: ProductStatusUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep = None,
) -> ProductResponseSchema:
    service = ProductService(session)
    product = await service.set_status(product_id, is_active=payload.is_active, actor=_actor_from_principal(principal))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product was not found.")
    await session.commit()
    return product

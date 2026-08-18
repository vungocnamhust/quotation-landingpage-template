from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DbSessionDep, EditorPrincipalDep
from repositories.quote_request_repository import QuoteRequestRepository
from schemas.v2.quote_request import (
    GenerateQuotationFromRequestResponseSchema,
    QuotationMinimalOverridesSchema,
    QuoteRequestCreateSchema,
    QuoteRequestEditPayloadSchema,
    QuoteRequestListResponseSchema,
    QuoteRequestResponseSchema,
    QuoteRequestRevisionDetailSchema,
    QuoteRequestRevisionSummarySchema,
    QuoteRequestRevisionsListResponseSchema,
    QuoteRequestUpdateSchema,
)
from services.quote_request_service import QuoteRequestService

router = APIRouter(
    prefix="/api/v2/workspace/requests",
    tags=["Quote Requests"],
)


@router.post("", response_model=QuoteRequestResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_quote_request(
    payload: QuoteRequestCreateSchema,
    session: DbSessionDep,
) -> QuoteRequestResponseSchema:
    service = QuoteRequestService(session)
    try:
        req = await service.create_quote_request(payload)
        await session.commit()
        await session.refresh(req)
        return QuoteRequestResponseSchema.model_validate(req)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("", response_model=QuoteRequestListResponseSchema)
async def list_quote_requests(
    session: DbSessionDep,
    q: Annotated[str, Query(description="Search by name, company, email, or ID")] = "",
    role: Annotated[str | None, Query(description="Filter by role persona (traveller, advisor)")] = None,
    req_status: Annotated[str | None, Query(alias="status", description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> QuoteRequestListResponseSchema:
    repo = QuoteRequestRepository(session)
    items, total = await repo.list_requests(
        search=q,
        role=role,
        status=req_status,
        limit=limit,
        offset=offset,
    )
    response_items = [QuoteRequestResponseSchema.model_validate(item) for item in items]
    return QuoteRequestListResponseSchema(
        items=response_items,
        total=total,
        next_cursor=str(offset + limit) if (offset + limit) < total else None,
        summary={"total": total, "returned": len(response_items)},
    )


@router.get("/{request_id}", response_model=QuoteRequestResponseSchema)
async def get_quote_request(
    request_id: str,
    session: DbSessionDep,
) -> QuoteRequestResponseSchema:
    repo = QuoteRequestRepository(session)
    req = await repo.get_by_id(request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"QuoteRequest {request_id} not found.")
    return QuoteRequestResponseSchema.model_validate(req)


@router.put("/{request_id}", response_model=QuoteRequestResponseSchema)
async def edit_quote_request(
    request_id: str,
    payload: QuoteRequestEditPayloadSchema,
    session: DbSessionDep,
) -> QuoteRequestResponseSchema:
    service = QuoteRequestService(session)
    try:
        req, _rev = await service.edit_quote_request(
            request_id=request_id,
            payload=payload,
            updated_by_profile_id=payload.travel_designer_id or payload.created_by_profile_id,
        )
        await session.commit()
        await session.refresh(req)
        return QuoteRequestResponseSchema.model_validate(req)
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/{request_id}/revisions", response_model=QuoteRequestRevisionsListResponseSchema)
async def list_quote_request_revisions(
    request_id: str,
    session: DbSessionDep,
) -> QuoteRequestRevisionsListResponseSchema:
    service = QuoteRequestService(session)
    try:
        revisions = await service.get_request_revisions(request_id)
        req = await service.repo.get_by_id(request_id)
        return QuoteRequestRevisionsListResponseSchema(
            request_id=request_id,
            current_revision=req.current_revision if req else 1,
            items=[QuoteRequestRevisionSummarySchema.model_validate(r) for r in revisions],
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.get("/{request_id}/revisions/{revision}", response_model=QuoteRequestRevisionDetailSchema)
async def get_quote_request_revision(
    request_id: str,
    revision: int,
    session: DbSessionDep,
) -> QuoteRequestRevisionDetailSchema:
    service = QuoteRequestService(session)
    try:
        rev = await service.get_request_revision(request_id, revision)
        return QuoteRequestRevisionDetailSchema.model_validate(rev)
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.patch("/{request_id}", response_model=QuoteRequestResponseSchema)
async def update_quote_request(
    request_id: str,
    payload: QuoteRequestUpdateSchema,
    session: DbSessionDep,
) -> QuoteRequestResponseSchema:
    repo = QuoteRequestRepository(session)
    req = await repo.get_by_id(request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"QuoteRequest {request_id} not found.")

    if payload.status:
        req.status = payload.status
    if payload.customer_name is not None:
        req.customer_name = payload.customer_name
    if payload.email is not None:
        req.email = payload.email
    if payload.phone is not None:
        req.phone = payload.phone
    if payload.company_name is not None:
        req.company_name = payload.company_name
    if payload.market is not None:
        req.market = payload.market
    if payload.special_requirements is not None:
        req.special_requirements = payload.special_requirements
    if payload.linked_quotation_id is not None:
        req.linked_quotation_id = payload.linked_quotation_id

    await session.commit()
    await session.refresh(req)
    return QuoteRequestResponseSchema.model_validate(req)


@router.post("/{request_id}/generate-quotation", response_model=GenerateQuotationFromRequestResponseSchema)
async def generate_quotation_from_request(
    request_id: str,
    session: DbSessionDep,
    overrides: QuotationMinimalOverridesSchema | None = None,
) -> GenerateQuotationFromRequestResponseSchema:
    service = QuoteRequestService(session)
    try:
        res = await service.generate_quotation_from_request(
            request_id=request_id,
            overrides=overrides,
        )
        await session.commit()
        return GenerateQuotationFromRequestResponseSchema(**res)
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate quotation: {err}") from err


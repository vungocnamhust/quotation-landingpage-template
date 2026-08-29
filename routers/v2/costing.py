"""V2 costing routes (15.4) — dual-track workbench, one file (§1.6)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status

from api.dependencies import DbSessionDep, EditorPrincipalDep, require_owned_v2_quotation
from core.kernel import ActorRef
from repositories.costing_repository import CostingRepository
from schemas.v2.costing import (
    ApplyPricingRequestSchema,
    ApplyPricingResponseSchema,
    AttachQuotationSchema,
    CostingSettingsUpdateSchema,
    CostingSheetCreateSchema,
    CostingSheetFindResponseSchema,
    CostingSheetResponseSchema,
    CostingWorkbenchResponseSchema,
    ServiceLineCreateSchema,
    ServiceLineUpdateSchema,
)
from services.costing_service import CostingConflictError, CostingService, CostingValidationError

router = APIRouter(prefix="/api/v2/costing-sheets", tags=["costing"])


def _actor_from_principal(principal: EditorPrincipalDep) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


def _conflict_detail(err: CostingConflictError) -> dict:
    return {"message": str(err), "currentRevision": err.current_revision}


def _validation_detail(err: CostingValidationError):
    """Keep structured 422 payloads (e.g. T6 rate candidates) machine-readable (16.3 F-17)."""
    payload = err.args[0] if err.args else str(err)
    return payload if isinstance(payload, dict) else str(payload)


async def _enforce_quotation_ownership_for_sheet(sheet_id: str, session, principal: EditorPrincipalDep) -> None:
    # Deliberate (16.3 F-28): a sheet not yet attached to a quotation has no owner —
    # any authenticated editor may work it, mirroring the unowned quote_request surface.
    sheet = await CostingRepository(session).get_sheet_by_id(sheet_id)
    if sheet is not None and sheet.quotation_id:
        await require_owned_v2_quotation(sheet.quotation_id, principal)


@router.post("", response_model=CostingSheetResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_costing_sheet(
    payload: CostingSheetCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> CostingSheetResponseSchema:
    if payload.quotation_id:
        await require_owned_v2_quotation(payload.quotation_id, principal)
    service = CostingService(session)
    try:
        sheet = await service.create_sheet(payload, actor=_actor_from_principal(principal))
        await session.commit()
        return sheet
    except CostingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_validation_detail(err)) from err
    except CostingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.get("", response_model=CostingSheetFindResponseSchema)
async def find_costing_sheet(
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    request_id: Annotated[str | None, Query(alias="requestId")] = None,
    quotation_id: Annotated[str | None, Query(alias="quotationId")] = None,
) -> CostingSheetFindResponseSchema:
    if bool(request_id) == bool(quotation_id):
        raise HTTPException(status_code=422, detail="Exactly one of requestId or quotationId is required.")
    service = CostingService(session)
    if quotation_id:
        await require_owned_v2_quotation(quotation_id, principal)
        sheet = await service.find_sheet_for_quotation(quotation_id)
    else:
        sheet = await service.find_sheet_for_request(request_id)
    if sheet is None:
        return CostingSheetFindResponseSchema(sheet=None)
    return CostingSheetFindResponseSchema(sheet=CostingSheetResponseSchema.model_validate(sheet))


@router.get("/{sheet_id}", response_model=CostingWorkbenchResponseSchema)
async def get_costing_workbench(
    sheet_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> CostingWorkbenchResponseSchema:
    await _enforce_quotation_ownership_for_sheet(sheet_id, session, principal)
    service = CostingService(session)
    workbench = await service.get_workbench(sheet_id)
    if workbench is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Costing sheet '{sheet_id}' was not found.")
    return workbench


@router.put("/{sheet_id}/settings", response_model=CostingWorkbenchResponseSchema)
async def update_costing_settings(
    sheet_id: str,
    payload: CostingSettingsUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> CostingWorkbenchResponseSchema:
    await _enforce_quotation_ownership_for_sheet(sheet_id, session, principal)
    service = CostingService(session)
    try:
        workbench = await service.update_settings(sheet_id, payload, actor=_actor_from_principal(principal))
        if workbench is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Costing sheet '{sheet_id}' was not found.")
        await session.commit()
        return workbench
    except CostingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.post("/{sheet_id}/attach-quotation", response_model=CostingWorkbenchResponseSchema)
async def attach_costing_sheet_to_quotation(
    sheet_id: str,
    payload: AttachQuotationSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> CostingWorkbenchResponseSchema:
    await require_owned_v2_quotation(payload.quotation_id, principal)
    service = CostingService(session)
    try:
        workbench = await service.attach_quotation(
            sheet_id, payload, actor=_actor_from_principal(principal), idempotency_key=idempotency_key
        )
        if workbench is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Costing sheet '{sheet_id}' was not found.")
        await session.commit()
        return workbench
    except CostingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_validation_detail(err)) from err
    except CostingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.post("/{sheet_id}/lines", response_model=CostingWorkbenchResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_service_line(
    sheet_id: str,
    payload: ServiceLineCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> CostingWorkbenchResponseSchema:
    await _enforce_quotation_ownership_for_sheet(sheet_id, session, principal)
    service = CostingService(session)
    try:
        workbench = await service.create_line(
            sheet_id, payload, actor=_actor_from_principal(principal), idempotency_key=idempotency_key
        )
        if workbench is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Costing sheet '{sheet_id}' was not found.")
        await session.commit()
        return workbench
    except CostingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_validation_detail(err)) from err
    except CostingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.put("/{sheet_id}/lines/{line_id}", response_model=CostingWorkbenchResponseSchema)
async def update_service_line(
    sheet_id: str,
    line_id: str,
    payload: ServiceLineUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> CostingWorkbenchResponseSchema:
    await _enforce_quotation_ownership_for_sheet(sheet_id, session, principal)
    service = CostingService(session)
    try:
        workbench = await service.update_line(sheet_id, line_id, payload, actor=_actor_from_principal(principal))
        if workbench is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service line '{line_id}' was not found.")
        await session.commit()
        return workbench
    except CostingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_validation_detail(err)) from err
    except CostingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.delete("/{sheet_id}/lines/{line_id}", response_model=CostingWorkbenchResponseSchema)
async def delete_service_line(
    sheet_id: str,
    line_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    base_costing_revision: Annotated[int, Query()],
) -> CostingWorkbenchResponseSchema:
    await _enforce_quotation_ownership_for_sheet(sheet_id, session, principal)
    service = CostingService(session)
    try:
        workbench = await service.delete_line(sheet_id, line_id, base_costing_revision=base_costing_revision)
        if workbench is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service line '{line_id}' was not found.")
        await session.commit()
        return workbench
    except CostingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.post("/{sheet_id}/apply-pricing", response_model=ApplyPricingResponseSchema)
async def apply_costing_pricing(
    sheet_id: str,
    payload: ApplyPricingRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ApplyPricingResponseSchema:
    await _enforce_quotation_ownership_for_sheet(sheet_id, session, principal)
    service = CostingService(session)
    try:
        response = await service.apply_pricing(
            sheet_id,
            payload,
            actor=_actor_from_principal(principal),
            idempotency_key=idempotency_key,
        )
        if response is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Costing sheet '{sheet_id}' was not found.")
        await session.commit()
        return response
    except CostingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=_validation_detail(err)) from err
    except CostingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


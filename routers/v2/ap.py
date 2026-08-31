"""V2 AP reconciliation routes (15.9) — supplier invoices, voucher matching, payments."""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from api.dependencies import DbSessionDep, EditorPrincipalDep, QuoteAdminPrincipalDep
from core.auth import require_quote_admin
from core.kernel import ActorRef
from schemas.v2.finance_ap import (
    ApPaymentResponseSchema,
    ApproveInvoiceRequestSchema,
    LineActionRequestSchema,
    MatchLineRequestSchema,
    RecordPaymentRequestSchema,
    SupplierInvoiceCreateSchema,
    SupplierInvoiceListResponseSchema,
    SupplierInvoiceResponseSchema,
    SupplierInvoiceLinesUpsertSchema,
    SupplierInvoiceUpdateSchema,
)
from services.ap_reconciliation_service import APConflictError, ApReconciliationService, APValidationError

router = APIRouter(prefix="/api/v2/ap", tags=["finance-ap"])


def _actor_from_principal(principal: EditorPrincipalDep) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


def _today() -> date:
    return date.today()


def _conflict_detail(err: APConflictError) -> dict:
    return {"message": str(err), "currentRevision": err.current_revision}


def _validation_detail(err: APValidationError):
    payload = err.args[0] if err.args else str(err)
    return payload if isinstance(payload, dict) else str(payload)


@router.post("/invoices", response_model=SupplierInvoiceResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: SupplierInvoiceCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    service = ApReconciliationService(session)
    try:
        invoice = await service.create_invoice(payload, actor=_actor_from_principal(principal), idempotency_key=idempotency_key)
        await session.commit()
        return invoice
    except APValidationError as err:
        raise HTTPException(status_code=422, detail=_validation_detail(err)) from err
    except APConflictError as err:
        raise HTTPException(status_code=409, detail=_conflict_detail(err)) from err


@router.get("/invoices", response_model=SupplierInvoiceListResponseSchema)
async def list_invoices(
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    supplier_id: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    due_within_days: Annotated[int | None, Query(alias="dueWithinDays")] = None,
    overdue_only: Annotated[bool, Query(alias="overdueOnly")] = False,
    search: Annotated[str | None, Query()] = None,
):
    service = ApReconciliationService(session)
    items = await service.list_invoices(
        supplier_id=supplier_id,
        status=status_filter,
        due_within_days=due_within_days,
        overdue_only=overdue_only,
        search=search,
        today=_today(),
    )
    return SupplierInvoiceListResponseSchema(items=items)


@router.get("/invoices/{invoice_id}", response_model=SupplierInvoiceResponseSchema)
async def get_invoice(invoice_id: str, session: DbSessionDep, principal: EditorPrincipalDep):
    service = ApReconciliationService(session)
    invoice = await service.get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"Supplier invoice '{invoice_id}' was not found.")
    return invoice


@router.put("/invoices/{invoice_id}", response_model=SupplierInvoiceResponseSchema)
async def update_invoice(
    invoice_id: str,
    payload: SupplierInvoiceUpdateSchema,
    request: Request,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
):
    if payload.action == "void":
        require_quote_admin(request)  # void moves invoices out of the ledger — admin-gated (§5.5 auth)
    service = ApReconciliationService(session)
    try:
        invoice = await service.update_header(invoice_id, payload, actor=_actor_from_principal(principal))
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Supplier invoice '{invoice_id}' was not found.")
        await session.commit()
        return invoice
    except APValidationError as err:
        raise HTTPException(status_code=422, detail=_validation_detail(err)) from err
    except APConflictError as err:
        raise HTTPException(status_code=409, detail=_conflict_detail(err)) from err


@router.put("/invoices/{invoice_id}/lines", response_model=SupplierInvoiceResponseSchema)
async def upsert_lines(
    invoice_id: str, payload: SupplierInvoiceLinesUpsertSchema, session: DbSessionDep, principal: EditorPrincipalDep
):
    service = ApReconciliationService(session)
    try:
        invoice = await service.upsert_lines(invoice_id, payload, actor=_actor_from_principal(principal))
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Supplier invoice '{invoice_id}' was not found.")
        await session.commit()
        return invoice
    except APValidationError as err:
        raise HTTPException(status_code=422, detail=_validation_detail(err)) from err
    except APConflictError as err:
        raise HTTPException(status_code=409, detail=_conflict_detail(err)) from err


@router.post("/invoices/{invoice_id}/lines/{line_id}/match", response_model=SupplierInvoiceResponseSchema)
async def match_line(
    invoice_id: str, line_id: int, payload: MatchLineRequestSchema, session: DbSessionDep, principal: EditorPrincipalDep
):
    service = ApReconciliationService(session)
    try:
        invoice = await service.match_line(invoice_id, line_id, payload, actor=_actor_from_principal(principal))
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Supplier invoice line '{line_id}' was not found.")
        await session.commit()
        return invoice
    except APValidationError as err:
        raise HTTPException(status_code=422, detail=_validation_detail(err)) from err
    except APConflictError as err:
        raise HTTPException(status_code=409, detail=_conflict_detail(err)) from err


@router.post("/invoices/{invoice_id}/lines/{line_id}/{action}", response_model=SupplierInvoiceResponseSchema)
async def line_action(
    invoice_id: str,
    line_id: int,
    action: Literal["unmatch", "waive", "dispute"],
    payload: LineActionRequestSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
):
    service = ApReconciliationService(session)
    try:
        invoice = await service.line_action(invoice_id, line_id, action, payload, actor=_actor_from_principal(principal))
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Supplier invoice line '{line_id}' was not found.")
        await session.commit()
        return invoice
    except APValidationError as err:
        raise HTTPException(status_code=422, detail=_validation_detail(err)) from err
    except APConflictError as err:
        raise HTTPException(status_code=409, detail=_conflict_detail(err)) from err


@router.post("/invoices/{invoice_id}/approve", response_model=SupplierInvoiceResponseSchema)
async def approve_invoice(
    invoice_id: str, payload: ApproveInvoiceRequestSchema, session: DbSessionDep, principal: QuoteAdminPrincipalDep
):
    service = ApReconciliationService(session)
    try:
        invoice = await service.approve(invoice_id, payload, actor=ActorRef(actor_id=principal.email or "unknown", actor_type="staff"))
        if invoice is None:
            raise HTTPException(status_code=404, detail=f"Supplier invoice '{invoice_id}' was not found.")
        await session.commit()
        return invoice
    except APValidationError as err:
        raise HTTPException(status_code=422, detail=_validation_detail(err)) from err
    except APConflictError as err:
        raise HTTPException(status_code=409, detail=_conflict_detail(err)) from err


@router.post("/payments", response_model=ApPaymentResponseSchema, status_code=status.HTTP_201_CREATED)
async def record_payment(
    payload: RecordPaymentRequestSchema,
    session: DbSessionDep,
    principal: QuoteAdminPrincipalDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    service = ApReconciliationService(session)
    try:
        payment = await service.record_payment(
            payload, actor=ActorRef(actor_id=principal.email or "unknown", actor_type="staff"), idempotency_key=idempotency_key
        )
        await session.commit()
        return payment
    except APValidationError as err:
        raise HTTPException(status_code=422, detail=_validation_detail(err)) from err
    except APConflictError as err:
        raise HTTPException(status_code=409, detail=_conflict_detail(err)) from err

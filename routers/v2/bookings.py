"""V2 booking routes (15.6) — Operations board, decoupled from the quotation workspace (§1.6)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status

from api.dependencies import DbSessionDep, EditorPrincipalDep, require_owned_v2_quotation
from core.kernel import ActorRef
from repositories.booking_repository import BookingRepository
from schemas.v2.booking import (
    BookingAddLineSchema,
    BookingBoardResponseSchema,
    BookingCancelSchema,
    BookingCreateSchema,
    BookingDetailResponseSchema,
    BookingHeaderUpdateSchema,
    BookingLineOpsUpdateSchema,
    BookingLineTransitionSchema,
)
from services.booking_service import BookingConflictError, BookingService, BookingValidationError

router = APIRouter(prefix="/api/v2/bookings", tags=["bookings"])


def _actor_from_principal(principal: EditorPrincipalDep) -> ActorRef:
    return ActorRef(actor_id=principal.email or "unknown", actor_type="staff")


def _conflict_detail(err: BookingConflictError) -> dict:
    return {"message": str(err), "currentRevision": err.current_revision}


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def _enforce_quotation_ownership_for_booking(booking_id: str, session, principal: EditorPrincipalDep) -> None:
    booking = await BookingRepository(session).get_booking_by_id(booking_id)
    if booking is not None:
        await require_owned_v2_quotation(booking.quotation_id, principal)


@router.post("", response_model=BookingDetailResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> BookingDetailResponseSchema:
    await require_owned_v2_quotation(payload.quotation_id, principal)
    service = BookingService(session)
    try:
        detail = await service.create_booking(
            payload, actor=_actor_from_principal(principal), idempotency_key=idempotency_key, today=_today()
        )
        await session.commit()
        return detail
    except BookingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except BookingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.get("", response_model=BookingBoardResponseSchema)
async def list_booking_board(
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    assignee: Annotated[str | None, Query()] = None,
    quotation_id: Annotated[str | None, Query(alias="quotationId")] = None,
    due_within_days: Annotated[int | None, Query(alias="dueWithinDays")] = None,
    overdue_only: Annotated[bool, Query(alias="overdueOnly")] = False,
) -> BookingBoardResponseSchema:
    if quotation_id:
        await require_owned_v2_quotation(quotation_id, principal)
    service = BookingService(session)
    return await service.list_board(
        today=_today(),
        status=status_filter,
        assignee_email=assignee,
        quotation_id=quotation_id,
        due_within_days=due_within_days,
        overdue_only=overdue_only,
    )


@router.get("/{booking_id}", response_model=BookingDetailResponseSchema)
async def get_booking(
    booking_id: str,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> BookingDetailResponseSchema:
    await _enforce_quotation_ownership_for_booking(booking_id, session, principal)
    service = BookingService(session)
    detail = await service.get_detail(booking_id, today=_today())
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking '{booking_id}' was not found.")
    return detail


@router.put("/{booking_id}", response_model=BookingDetailResponseSchema)
async def update_booking_header(
    booking_id: str,
    payload: BookingHeaderUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> BookingDetailResponseSchema:
    await _enforce_quotation_ownership_for_booking(booking_id, session, principal)
    service = BookingService(session)
    try:
        detail = await service.update_header(booking_id, payload, actor=_actor_from_principal(principal), today=_today())
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking '{booking_id}' was not found.")
        await session.commit()
        return detail
    except BookingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.post("/{booking_id}/lines/{line_id}/transition", response_model=BookingDetailResponseSchema)
async def transition_booking_line(
    booking_id: str,
    line_id: str,
    payload: BookingLineTransitionSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> BookingDetailResponseSchema:
    await _enforce_quotation_ownership_for_booking(booking_id, session, principal)
    service = BookingService(session)
    try:
        detail = await service.transition_line(
            booking_id,
            line_id,
            payload,
            actor=_actor_from_principal(principal),
            idempotency_key=idempotency_key,
            today=_today(),
        )
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking line '{line_id}' was not found.")
        await session.commit()
        return detail
    except BookingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except BookingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.put("/{booking_id}/lines/{line_id}", response_model=BookingDetailResponseSchema)
async def update_booking_line_ops(
    booking_id: str,
    line_id: str,
    payload: BookingLineOpsUpdateSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> BookingDetailResponseSchema:
    await _enforce_quotation_ownership_for_booking(booking_id, session, principal)
    service = BookingService(session)
    try:
        detail = await service.update_line_ops(booking_id, line_id, payload, actor=_actor_from_principal(principal), today=_today())
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking line '{line_id}' was not found.")
        await session.commit()
        return detail
    except BookingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except BookingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.post("/{booking_id}/lines", response_model=BookingDetailResponseSchema, status_code=status.HTTP_201_CREATED)
async def add_booking_line(
    booking_id: str,
    payload: BookingAddLineSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> BookingDetailResponseSchema:
    await _enforce_quotation_ownership_for_booking(booking_id, session, principal)
    service = BookingService(session)
    try:
        detail = await service.add_line(booking_id, payload, actor=_actor_from_principal(principal), today=_today())
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking '{booking_id}' was not found.")
        await session.commit()
        return detail
    except BookingValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except BookingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err


@router.post("/{booking_id}/cancel", response_model=BookingDetailResponseSchema)
async def cancel_booking(
    booking_id: str,
    payload: BookingCancelSchema,
    session: DbSessionDep,
    principal: EditorPrincipalDep,
) -> BookingDetailResponseSchema:
    await _enforce_quotation_ownership_for_booking(booking_id, session, principal)
    service = BookingService(session)
    try:
        detail = await service.cancel_booking(booking_id, payload, actor=_actor_from_principal(principal), today=_today())
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking '{booking_id}' was not found.")
        await session.commit()
        return detail
    except BookingConflictError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_conflict_detail(err)) from err

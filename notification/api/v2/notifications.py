from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, status

from notification.api.dependencies import EditorPrincipalDep, NotificationDbDep
from notification.api.schemas import (
    MarkAllReadResponseSchema,
    MarkReadResponseSchema,
    NotificationItemSchema,
    NotificationListResponseSchema,
    UnreadCountResponseSchema,
)
from notification.application.manage_inbox import (
    MarkReadUseCase,
    QueryInboxUseCase,
)

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponseSchema)
async def list_notifications(
    session: NotificationDbDep,
    principal: EditorPrincipalDep,
    is_read: Annotated[bool | None, Query(description="Filter by read state")] = None,
    severity: Annotated[str | None, Query(description="Filter by severity")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationListResponseSchema:
    email = (principal.email or "all@workspace.internal").strip().lower()
    use_case = QueryInboxUseCase(session)
    items, total, unread_count = await use_case.list_notifications(
        recipient_email=email,
        is_read=is_read,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    schema_items = [
        NotificationItemSchema(
            id=item.id,
            source_service=item.source_service,
            source_event_id=item.source_event_id,
            notification_type=item.notification_type,
            recipient_email=item.recipient_email,
            recipient_profile_id=item.recipient_profile_id,
            brand_id=item.brand_id,
            title=item.title,
            body=item.body,
            severity=item.severity,
            action_url=item.action_url,
            aggregate_type=item.aggregate_type,
            aggregate_id=item.aggregate_id,
            metadata_json=item.metadata_json,
            is_read=item.is_read,
            read_at=item.read_at,
            created_at=item.created_at,
        )
        for item in items
    ]
    return NotificationListResponseSchema(
        items=schema_items,
        total=total,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=UnreadCountResponseSchema)
async def get_unread_count(
    session: NotificationDbDep,
    principal: EditorPrincipalDep,
) -> UnreadCountResponseSchema:
    email = (principal.email or "all@workspace.internal").strip().lower()
    use_case = QueryInboxUseCase(session)
    count = await use_case.get_unread_count(email)
    return UnreadCountResponseSchema(unread_count=count)


@router.patch("/{notification_id}/read", response_model=MarkReadResponseSchema)
async def mark_notification_read(
    notification_id: str,
    session: NotificationDbDep,
    principal: EditorPrincipalDep,
) -> MarkReadResponseSchema:
    email = (principal.email or "all@workspace.internal").strip().lower()
    use_case = MarkReadUseCase(session)
    notif = await use_case.mark_read(notification_id, email)
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification '{notification_id}' not found or unauthorized.",
        )
    return MarkReadResponseSchema(
        success=True,
        notification_id=notification_id,
        is_read=True,
    )


@router.post("/mark-all-read", response_model=MarkAllReadResponseSchema)
async def mark_all_notifications_read(
    session: NotificationDbDep,
    principal: EditorPrincipalDep,
) -> MarkAllReadResponseSchema:
    email = (principal.email or "all@workspace.internal").strip().lower()
    use_case = MarkReadUseCase(session)
    marked_count, unread_count = await use_case.mark_all_read(email)
    return MarkAllReadResponseSchema(
        success=True,
        marked_count=marked_count,
        unread_count=unread_count,
    )

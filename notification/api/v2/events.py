from __future__ import annotations

from fastapi import APIRouter, status
from notification.api.dependencies import EditorOrServicePrincipalDep, NotificationDbDep
from notification.api.schemas import IngestEventResponseSchema
from notification.application.ingest_event import IngestEventUseCase
from notification.domain.events import IntegrationEvent

router = APIRouter(prefix="/api/v2/events", tags=["events"])


@router.post("", response_model=IngestEventResponseSchema, status_code=status.HTTP_201_CREATED)
async def ingest_event(
    event: IntegrationEvent,
    session: NotificationDbDep,
    _principal: EditorOrServicePrincipalDep,
) -> IngestEventResponseSchema:
    use_case = IngestEventUseCase(session)
    notifications = await use_case.execute(event)
    return IngestEventResponseSchema(
        success=True,
        event_id=event.event_id,
        notifications_created=len(notifications),
    )

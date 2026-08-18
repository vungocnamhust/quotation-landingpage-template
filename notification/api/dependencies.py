from __future__ import annotations

from typing import Annotated
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import Principal, require_editor, require_editor_or_service
from notification.infrastructure.db.base import get_notification_db


def get_notification_principal(request: Request) -> Principal:
    email = request.headers.get("X-DMC-Email")
    if email and email.strip():
        return Principal(
            email=email.strip().lower(),
            person_id=request.headers.get("X-DMC-Person-Id"),
            brand=request.headers.get("X-DMC-Brand"),
            role=request.headers.get("X-DMC-Role"),
            source="dmc_gateway",
        )
    return require_editor(request)


NotificationDbDep = Annotated[AsyncSession, Depends(get_notification_db)]
EditorPrincipalDep = Annotated[Principal, Depends(get_notification_principal)]
EditorOrServicePrincipalDep = Annotated[Principal, Depends(require_editor_or_service)]

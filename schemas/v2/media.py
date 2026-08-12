"""Legacy-compatible V2 media request schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MediaSelectionRequest(BaseModel):
    quotationId: str
    lang: str = "all"
    sectionKey: str
    slotKey: str
    displayOrder: int = Field(default=0, ge=0)


class MediaSyncRequest(BaseModel):
    folder: str = ""
    recursive: bool = True
    quotationId: Optional[str] = None

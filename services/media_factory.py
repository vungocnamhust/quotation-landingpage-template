"""Media service singletons and storage backend resolution factory."""

import os
import sys
from fastapi import HTTPException
from core.config import settings
from db.session import get_session_factory
from services.media_service import MediaService
from services.media_library_service import MediaLibraryService
from services.storage.local_media_storage import LocalMediaStorage
from services.storage.r2_storage import R2Storage

_media_service: MediaService | None = None
_media_library_service: MediaLibraryService | None = None


def get_media_service() -> MediaService:
    global _media_service
    main_mod = sys.modules.get("main")
    if main_mod and hasattr(main_mod, "_media_service") and main_mod._media_service is None:
        _media_service = None

    media_backend = (os.getenv("MEDIA_STORAGE_BACKEND") or "").strip().lower()
    use_r2_storage = media_backend == "r2" or (not media_backend and settings.has_r2_configuration)
    desired_storage_class = R2Storage if use_r2_storage else LocalMediaStorage

    if _media_service is None or not isinstance(_media_service.storage, desired_storage_class):
        storage = desired_storage_class()
        _media_service = MediaService(storage=storage)
    if main_mod:
        main_mod._media_service = _media_service
    return _media_service


def get_media_library_service() -> MediaLibraryService:
    global _media_library_service
    main_mod = sys.modules.get("main")
    if main_mod and hasattr(main_mod, "_media_library_service") and main_mod._media_library_service is None:
        _media_library_service = None

    if not settings.has_r2_configuration:
        raise HTTPException(status_code=503, detail="R2 media library is not configured.")
    if _media_library_service is None:
        _media_library_service = MediaLibraryService(storage=R2Storage(), session_factory=get_session_factory())
    if main_mod:
        main_mod._media_library_service = _media_library_service
    return _media_library_service


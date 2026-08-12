"""Runtime adapters configured by the ASGI composition root.

Routers depend on these narrow callbacks instead of importing ``main``.  The
application supplies the legacy-compatible implementations at startup, which
also preserves the existing test seams that patch those functions.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


MediaServiceProvider = Callable[[], Any]
SessionFactoryProvider = Callable[[], Any]
LoadContextProvider = Callable[[str], dict[str, Any] | None]
DatabaseUnavailablePredicate = Callable[[BaseException], bool]
DraftAssetStore = Callable[..., Awaitable[dict[str, Any]]]
TravelDesignerSerializer = Callable[[Any], dict[str, Any]]
QuotationWorkflowLoader = Callable[[str], Awaitable[dict[str, Any]]]

_media_service_provider: MediaServiceProvider | None = None
_session_factory_provider: SessionFactoryProvider | None = None
_load_context_provider: LoadContextProvider | None = None
_database_unavailable_predicate: DatabaseUnavailablePredicate | None = None
_draft_asset_store: DraftAssetStore | None = None
_travel_designer_serializer: TravelDesignerSerializer | None = None
_quotation_workflow_loader: QuotationWorkflowLoader | None = None


def configure_v2_runtime(
    *,
    media_service_provider: MediaServiceProvider,
    session_factory_provider: SessionFactoryProvider,
    load_context_provider: LoadContextProvider,
    database_unavailable_predicate: DatabaseUnavailablePredicate,
    draft_asset_store: DraftAssetStore,
    travel_designer_serializer: TravelDesignerSerializer,
    quotation_workflow_loader: QuotationWorkflowLoader,
) -> None:
    global _media_service_provider, _session_factory_provider, _load_context_provider
    global _database_unavailable_predicate, _draft_asset_store
    global _travel_designer_serializer, _quotation_workflow_loader
    _media_service_provider = media_service_provider
    _session_factory_provider = session_factory_provider
    _load_context_provider = load_context_provider
    _database_unavailable_predicate = database_unavailable_predicate
    _draft_asset_store = draft_asset_store
    _travel_designer_serializer = travel_designer_serializer
    _quotation_workflow_loader = quotation_workflow_loader


def _configured(value: Any, name: str) -> Any:
    if value is None:
        raise RuntimeError(f"V2 runtime adapter '{name}' was not configured by the application.")
    return value


def get_media_service() -> Any:
    return _configured(_media_service_provider, "media_service_provider")()


def get_session_factory() -> Any:
    return _configured(_session_factory_provider, "session_factory_provider")()


def load_context(quotation_id: str) -> dict[str, Any] | None:
    return _configured(_load_context_provider, "load_context_provider")(quotation_id)


def is_database_unavailable(exc: BaseException) -> bool:
    return _configured(_database_unavailable_predicate, "database_unavailable_predicate")(exc)


async def store_draft_asset(**kwargs: Any) -> dict[str, Any]:
    return await _configured(_draft_asset_store, "draft_asset_store")(**kwargs)


def serialize_travel_designer(profile: Any) -> dict[str, Any]:
    return _configured(_travel_designer_serializer, "travel_designer_serializer")(profile)


async def load_quotation_workflow(quotation_id: str) -> dict[str, Any]:
    return await _configured(_quotation_workflow_loader, "quotation_workflow_loader")(quotation_id)

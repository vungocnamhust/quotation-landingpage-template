"""Staff workspace routes."""
from __future__ import annotations

from fastapi import APIRouter

from api import runtime
from api.dependencies import EditorPrincipalDep, OwnedV2QuotationDep, get_active_travel_designer
from services.workspace_service import get_workspace_overview, list_workspace_quotations as list_workspace_quotations_service


router = APIRouter(prefix="/api/v2/workspace", tags=["workspace"])


@router.get("/me")
async def get_workspace_me(principal: EditorPrincipalDep) -> dict:
    profile = await get_active_travel_designer(principal)
    return {"profile": runtime.serialize_travel_designer(profile), "capabilities": {"createQuotation": True}}


@router.get("/quotations")
async def list_workspace_quotations(
    principal: EditorPrincipalDep,
    status: str | None = None,
    q: str = "",
    cursor: str | None = None,
    limit: int = 20,
) -> dict:
    del principal
    return await list_workspace_quotations_service(
        runtime.get_session_factory(), status=status, query=q, cursor=cursor, limit=limit,
    )


@router.get("/quotations/{quotation_id}/overview")
async def get_workspace_quotation_overview(quotation_id: str, _owned: OwnedV2QuotationDep) -> dict:
    del _owned
    workflow = await runtime.load_quotation_workflow(quotation_id)
    return await get_workspace_overview(runtime.get_session_factory(), quotation_id, workflow)

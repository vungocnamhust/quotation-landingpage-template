"""Public brochure and PDF rendering routes."""
from __future__ import annotations

import mimetypes
import os
from typing import Annotated
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
import httpx


router = APIRouter(tags=["public-brochure"])


def _get_helpers():
    import main
    return main


@router.get("/published/{quotation_id}/version")
async def get_published_version(quotation_id: str):
    from github_publish import get_next_version
    try:
        next_ver = await get_next_version(quotation_id)
        latest_ver = max(1, next_ver - 1)
    except Exception:
        latest_ver = 1
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return JSONResponse(
        content={
            "version": latest_ver,
            "latest_url": f"/published/{quotation_id}/v{latest_ver}.html",
        },
        headers=no_cache_headers,
    )


@router.get("/published/{quotation_id}")
@router.get("/published/{quotation_id}/latest")
async def redirect_to_latest_published(quotation_id: str):
    from github_publish import get_next_version
    try:
        next_ver = await get_next_version(quotation_id)
        latest_ver = max(1, next_ver - 1)
    except Exception:
        latest_ver = 1
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return RedirectResponse(
        url=f"/published/{quotation_id}/v{latest_ver}.html",
        status_code=307,
        headers=no_cache_headers,
    )


@router.get("/published/{file_path:path}")
async def get_published_file(file_path: str):
    h = _get_helpers()
    local_path = os.path.join("published", file_path)
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if os.path.exists(local_path) and os.path.isfile(local_path):
        mime, _ = mimetypes.guess_type(local_path)
        return FileResponse(
            local_path,
            media_type=mime or "application/octet-stream",
            headers=no_cache_headers,
        )
    github_content = await h._fetch_published_file_from_github(file_path)
    if github_content is not None:
        mime, _ = mimetypes.guess_type(file_path)
        return Response(
            content=github_content,
            media_type=mime or "text/html",
            headers=no_cache_headers,
        )
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/quotations/{quotation_id}/pdf", response_class=HTMLResponse)
async def get_quotation_pdf(quotation_id: str, request: Request):
    h = _get_helpers()
    lang = request.query_params.get("lang") or request.query_params.get("language")
    if lang not in ("en", "vi", "ar"):
        lang = None

    ctx_data = h._load_ctx_data(quotation_id)
    if not ctx_data:
        raise HTTPException(status_code=404, detail=f"PDF for quotation '{quotation_id}' not found.")

    baseline_lang = ctx_data.get("baseline_lang", "en")
    target_lang = lang or baseline_lang
    preview_mode = request.query_params.get("preview") in {"1", "true", "yes"}
    requested_brand = request.query_params.get("brand")
    template_name = ctx_data.get("template_name", h.BROCHURE_TEMPLATE_NAME)

    use_static_pdf_cache = (
        not preview_mode
        and not requested_brand
        and template_name not in h.LEGACY_QUOTATION_TEMPLATES
    )

    if use_static_pdf_cache:
        published_pdf = await h._get_latest_published_pdf_html(quotation_id, target_lang)
        if published_pdf:
            return HTMLResponse(content=published_pdf)

    if target_lang != baseline_lang:
        available_langs = ctx_data.get("available_langs", [])
        if target_lang not in available_langs:
            success = await h._translate_item_on_demand(quotation_id, target_lang, is_itinerary=False)
            if success:
                ctx_data = h._load_ctx_data(quotation_id) or ctx_data

    effective_lang = target_lang if target_lang in ctx_data.get("available_langs", [baseline_lang]) else baseline_lang

    try:
        rendered_html, _ = await h._render_quotation_html_for_lang(
            quotation_id,
            effective_lang,
            pdf_mode=True,
            request=request,
            requested_brand=requested_brand,
            preview_mode=preview_mode,
        )
        if h._is_brochure_template(ctx_data.get("template_name", "vietnam_luxury_brosure.html")):
            lang_ctx, _, _ = await h._build_quotation_lang_ctx(
                ctx_data,
                quotation_id,
                effective_lang,
                request,
                ignore_published_html=True,
                force_editor_draft=preview_mode,
            )
            draft = h._ensure_brochure_draft(ctx_data, quotation_id, effective_lang, lang_ctx, force_brand_from_ctx=preview_mode)
            h._store_brochure_draft(ctx_data, effective_lang, draft)
        return HTMLResponse(content=rendered_html)
    except Exception as err:
        h.log.exception("[/quotations] Dynamic PDF render failed for %s: %s", quotation_id, err)
        raise HTTPException(status_code=500, detail=f"PDF render error: {err}")

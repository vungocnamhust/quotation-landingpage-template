"""Quotation V2 presentation overrides and sync payload validation helpers."""

import copy
from typing import Any
from fastapi import HTTPException
from core.brands import BRAND_OWNED_CTX_FIELDS, BRAND_OWNED_EDITABLE_FIELDS
from editable_brochure_contract import design_identity_field, is_design_copy_field


def _validate_v2_copy_overrides(overrides: Any) -> dict[str, str]:
    if not isinstance(overrides, dict):
        raise HTTPException(status_code=422, detail={"message": "copyOverrides must be an object."})
    invalid = [key for key, value in overrides.items()
               if not is_design_copy_field(key) or not isinstance(value, str)
               or not value.strip() or len(value) > 500]
    if invalid:
        raise HTTPException(status_code=422, detail={
            "message": "copyOverrides contains an invalid presentation key or value.",
            "invalidKeys": sorted(str(key) for key in invalid),
        })
    return {key: value.strip() for key, value in overrides.items()}


def _validate_v2_media_overrides(overrides: Any) -> dict[str, Any]:
    if not isinstance(overrides, dict):
        raise HTTPException(status_code=422, detail={"message": "mediaOverrides must be an object."})
    if overrides:
        raise HTTPException(status_code=422, detail={"message": "mediaOverrides is legacy read-only. Save quotation media through /facts/media slots."})
    return {}


def _validate_v2_identity_overrides(overrides: Any) -> dict[str, str]:
    if not isinstance(overrides, dict):
        raise HTTPException(status_code=422, detail={"message": "identityOverrides must be an object."})
    invalid: list[str] = []
    normalized: dict[str, str] = {}
    for key, value in overrides.items():
        limit = 160 if key == "brandName" else 500
        if design_identity_field(str(key)) is None or not isinstance(value, str) or not value.strip() or len(value) > limit:
            invalid.append(str(key))
            continue
        normalized[str(key)] = value.strip()
    if invalid:
        raise HTTPException(status_code=422, detail={
            "message": "identityOverrides contains an invalid Design field or value.",
            "invalidKeys": sorted(invalid),
        })
    return normalized


def _sanitize_html_sync_payload(
    existing_keys: set[str] | None,
    edited_fields: dict | None,
    composite_fields: dict | None = None,
):
    safe_existing_keys = {
        key for key in (existing_keys or set())
        if key not in BRAND_OWNED_EDITABLE_FIELDS
    }
    safe_edited_fields = {
        key: value
        for key, value in (edited_fields or {}).items()
        if key not in BRAND_OWNED_EDITABLE_FIELDS
    }

    safe_composite_fields = copy.deepcopy(composite_fields or {})
    top_level = safe_composite_fields.get("top_level", {})
    if top_level:
        safe_top_level = {
            key: value
            for key, value in top_level.items()
            if key not in BRAND_OWNED_CTX_FIELDS
        }
        if safe_top_level:
            safe_composite_fields["top_level"] = safe_top_level
        else:
            safe_composite_fields.pop("top_level", None)

    return safe_existing_keys, safe_edited_fields, safe_composite_fields

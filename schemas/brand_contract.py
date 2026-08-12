"""Brand render profile contract, contrast calculation, and brand profile serialization."""

import copy
import re
from typing import Any, Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from quote_document import BrandContentPolicy, BrandProfile
from repositories import BrandRepository
from db.session import get_session_factory


def _relative_luminance(hex_color: str) -> float:
    """Return WCAG relative luminance for an already-validated #RRGGBB value."""
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    normalized = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * normalized[0] + 0.7152 * normalized[1] + 0.0722 * normalized[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter = max(_relative_luminance(foreground), _relative_luminance(background))
    darker = min(_relative_luminance(foreground), _relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


class BrandRenderProfileContract(BaseModel):
    """Mutable brand configuration; release snapshots use the serialized form."""

    model_config = ConfigDict(extra="allow")
    palette: dict[str, str]
    radii: dict[str, str]
    themeId: Literal["brochure"] = "brochure"
    layoutVersion: int = 1

    @field_validator("palette")
    @classmethod
    def validate_palette(cls, palette: dict[str, str]) -> dict[str, str]:
        required = {"canvas", "paper", "ink", "mutedInk", "accent", "accentAlt", "contrast", "onContrast", "focus"}
        section_backgrounds = {"storyContrast", "investmentSurface", "investmentText"}
        if missing := required.difference(palette):
            raise ValueError(f"palette is missing required colors: {', '.join(sorted(missing))}")
        if section_backgrounds.intersection(palette):
            if missing := section_backgrounds.difference(palette):
                raise ValueError(
                    "palette section-background colors must be supplied together: "
                    f"{', '.join(sorted(missing))}"
                )
        if invalid := [key for key, value in palette.items() if not re.fullmatch(r"#[0-9a-fA-F]{6}", value)]:
            raise ValueError(f"palette contains invalid #RRGGBB values: {', '.join(sorted(invalid))}")
        checks = (
            ("ink", "canvas", 4.5, "body text"),
            ("onContrast", "contrast", 4.5, "contrast text"),
            ("focus", "canvas", 3.0, "focus ring"),
        )
        if section_backgrounds.issubset(palette):
            checks += (
                ("onContrast", "storyContrast", 4.5, "story contrast text"),
                ("investmentText", "investmentSurface", 4.5, "investment text"),
            )
        for foreground, background, minimum, label in checks:
            ratio = _contrast_ratio(palette[foreground], palette[background])
            if ratio < minimum:
                raise ValueError(
                    f"{label} contrast is {ratio:.2f}:1; required minimum is {minimum}:1"
                )
        return palette

    @field_validator("radii")
    @classmethod
    def validate_radii(cls, radii: dict[str, str]) -> dict[str, str]:
        required = {"card", "button", "frame", "pill"}
        if missing := required.difference(radii):
            raise ValueError(f"radii is missing required values: {', '.join(sorted(missing))}")
        if any(not value.strip() for value in radii.values()):
            raise ValueError("radii values must not be empty")
        if re.fullmatch(r"\s*(?:999+px|50%|100%)\s*", radii["button"], flags=re.IGNORECASE):
            raise ValueError("radii.button must be a component radius, not a pill radius")
        return radii

    @model_validator(mode="after")
    def validate_layout(self):
        if self.layoutVersion != 1:
            raise ValueError("layoutVersion 1 is the only supported V2 layout")
        return self


def _serialize_brand_render_profile(brand: Any) -> dict[str, Any]:
    profile = copy.deepcopy(brand.render_profile or {})
    BrandRenderProfileContract.model_validate(profile)
    profile.update({
        "id": brand.id,
        "displayName": brand.display_name,
        "hostname": brand.hostname,
        "logoUrl": profile.get("logoUrl") or brand.logo_asset_key or "",
    })
    return profile


def _brand_generation_profile(brand: Any) -> BrandProfile:
    profile = _serialize_brand_render_profile(brand)
    content_policy = profile.get("contentPolicy") if isinstance(profile.get("contentPolicy"), dict) else {}
    return BrandProfile(
        brand_id=brand.id,
        display_name=brand.display_name,
        domain=brand.hostname,
        logo=profile.get("logoUrl") or "",
        colors=profile.get("palette") if isinstance(profile.get("palette"), dict) else {},
        fonts=profile.get("typography") if isinstance(profile.get("typography"), dict) else {},
        content_policy=BrandContentPolicy.model_validate(content_policy),
    )


def _get_db_session_factory():
    import sys
    main_mod = sys.modules.get("main")
    if main_mod and hasattr(main_mod, "_get_db_session_factory"):
        return main_mod._get_db_session_factory()
    return get_session_factory()


async def _require_active_v2_brand(brand_id: str | None) -> Any:
    if not brand_id:
        raise HTTPException(status_code=422, detail={"message": "An active brand is required.", "missingInputs": ["brand_id"]})
    async with _get_db_session_factory()() as session:
        brand = await BrandRepository(session).get_active(brand_id)
        if brand is None:
            raise HTTPException(status_code=422, detail={"message": "Brand is unavailable for V2.", "missingInputs": ["brand_id"]})
        return brand


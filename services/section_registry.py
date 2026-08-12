"""Section definitions, default layout sections, and validation logic for QuoteDocumentV1."""

from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field
from schemas.quote_document.brand import QuoteBaseModel

SECTION_TYPES = (
    "hero",
    "overview_letter",
    "route_map",
    "itinerary",
    "hotel_plan",
    "pricing",
    "inclusions_exclusions",
    "booking_terms",
    "designer",
    "finalization",
)


class QuoteSection(QuoteBaseModel):
    id: str
    type: Literal[
        "hero",
        "overview_letter",
        "route_map",
        "itinerary",
        "hotel_plan",
        "pricing",
        "inclusions_exclusions",
        "booking_terms",
        "designer",
        "finalization",
    ]
    enabled: bool = True
    order: int = 0
    props: Dict[str, Any] = Field(default_factory=dict)


class SectionDefinition(QuoteBaseModel):
    type: str
    label: str
    props_schema: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    editor_schema: Dict[str, Any] = Field(default_factory=dict)
    web_anchor: str = ""
    pdf_anchor: str = ""
    required_document_paths: List[str] = Field(default_factory=list)
    allow_multiple: bool = False


class SectionValidationError(QuoteBaseModel):
    sectionId: str
    sectionType: str
    code: str
    message: str
    path: str


def build_default_sections() -> List[QuoteSection]:
    return [
        QuoteSection(id="hero", type="hero", enabled=True, order=1),
        QuoteSection(id="overview_letter", type="overview_letter", enabled=True, order=2),
        QuoteSection(id="route_map", type="route_map", enabled=True, order=3),
        QuoteSection(id="itinerary", type="itinerary", enabled=True, order=4),
        QuoteSection(id="hotel_plan", type="hotel_plan", enabled=True, order=5),
        QuoteSection(id="pricing", type="pricing", enabled=True, order=6),
        QuoteSection(id="inclusions_exclusions", type="inclusions_exclusions", enabled=True, order=7),
        QuoteSection(id="booking_terms", type="booking_terms", enabled=True, order=8),
        QuoteSection(id="designer", type="designer", enabled=True, order=9),
        QuoteSection(id="finalization", type="finalization", enabled=True, order=10),
    ]


SECTION_REGISTRY: Dict[str, SectionDefinition] = {
    "hero": SectionDefinition(
        type="hero",
        label="Hero",
        web_anchor="hero",
        pdf_anchor="hero",
        required_document_paths=["trip.title", "trip.lede", "assets.hero"],
        editor_schema={"fields": ["trip.title", "trip.lede", "assets.hero"]},
    ),
    "overview_letter": SectionDefinition(
        type="overview_letter",
        label="Overview Letter",
        web_anchor="overview_letter",
        pdf_anchor="overview_letter",
        required_document_paths=["narrative.letterIntro", "narrative.letterBody2"],
        editor_schema={"fields": ["narrative.letterGreeting", "narrative.letterIntro", "narrative.letterBody2", "narrative.letterOutro"]},
    ),
    "route_map": SectionDefinition(
        type="route_map",
        label="Route Map",
        web_anchor="route_map",
        pdf_anchor="route_map",
        required_document_paths=["route.staySegments"],
        editor_schema={"fields": ["route.title", "route.description", "route.staySegments"]},
    ),
    "itinerary": SectionDefinition(
        type="itinerary",
        label="Itinerary",
        web_anchor="itinerary",
        pdf_anchor="itinerary",
        required_document_paths=["itinerary.days"],
        editor_schema={"fields": ["itinerary.title", "itinerary.description", "itinerary.days"]},
    ),
    "hotel_plan": SectionDefinition(
        type="hotel_plan",
        label="Hotel Plan",
        web_anchor="hotel_plan",
        pdf_anchor="hotel_plan",
        required_document_paths=["stays.hotels"],
        editor_schema={"fields": ["stays.hotels", "stays.roomNotes"]},
    ),
    "pricing": SectionDefinition(
        type="pricing",
        label="Pricing",
        web_anchor="pricing",
        pdf_anchor="pricing",
        required_document_paths=["pricing.options"],
        editor_schema={"fields": ["pricing.conditions", "pricing.options"]},
    ),
    "inclusions_exclusions": SectionDefinition(
        type="inclusions_exclusions",
        label="Inclusions & Exclusions",
        web_anchor="inclusions_exclusions",
        pdf_anchor="inclusions_exclusions",
        required_document_paths=["content.sections.inclusions_exclusions.blocks"],
        editor_schema={"fields": ["content.sections.inclusions_exclusions.blocks"]},
    ),
    "booking_terms": SectionDefinition(
        type="booking_terms",
        label="Booking Terms",
        web_anchor="booking_terms",
        pdf_anchor="booking_terms",
        required_document_paths=["content.sections.booking_terms.blocks"],
        editor_schema={"fields": ["content.sections.booking_terms.blocks"]},
    ),
    "designer": SectionDefinition(
        type="designer",
        label="Designer",
        web_anchor="designer",
        pdf_anchor="designer",
        required_document_paths=["designer.name"],
        editor_schema={"fields": ["designer.name", "designer.signature", "designer.title", "designer.experience", "designer.quote", "designer.phone", "designer.email", "designer.image"]},
    ),
    "finalization": SectionDefinition(
        type="finalization",
        label="Finalization",
        web_anchor="finalization",
        pdf_anchor="finalization",
        required_document_paths=[],
        editor_schema={"fields": ["content.sections.finalization.blocks"]},
    ),
}


def _path_exists(payload: Any, path: str) -> bool:
    current = payload
    for part in path.split("."):
        if isinstance(current, BaseModel):
            current = getattr(current, part, None)
            continue
        if isinstance(current, dict):
            current = current.get(part)
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return bool(current)
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
            continue
        return False
    if isinstance(current, list):
        return len(current) > 0
    if isinstance(current, BaseModel):
        current = current.model_dump(mode="json")
    if isinstance(current, dict) and {"assetId", "r2Key", "url"}.intersection(current):
        return bool(current.get("assetId") or current.get("r2Key") or current.get("url"))
    return current not in (None, "", {}, [])


def validate_quote_document_sections(document: Any) -> List[SectionValidationError]:
    from quote_document import QuoteDocumentV1
    errors: List[SectionValidationError] = []
    if isinstance(document, dict):
        raw_sections = (((document.get("layout") or {}).get("sections")) if isinstance(document.get("layout"), dict) else None) or []
        seen_types: Dict[str, str] = {}
        for index, raw_section in enumerate(raw_sections):
            if not isinstance(raw_section, dict):
                errors.append(
                    SectionValidationError(
                        sectionId=f"section-{index + 1}",
                        sectionType="",
                        code="invalid_section_payload",
                        message="Each section must be an object payload.",
                        path=f"layout.sections.{index}",
                    )
                )
                continue
            section_type = str(raw_section.get("type") or "")
            section_id = str(raw_section.get("id") or section_type or f"section-{index + 1}")
            definition = SECTION_REGISTRY.get(section_type)
            if definition is None:
                errors.append(
                    SectionValidationError(
                        sectionId=section_id,
                        sectionType=section_type,
                        code="unknown_section_type",
                        message=f"Section type '{section_type}' is not registered.",
                        path=f"layout.sections.{index}.type",
                    )
                )
                continue
            if not definition.allow_multiple and section_type in seen_types:
                errors.append(
                    SectionValidationError(
                        sectionId=section_id,
                        sectionType=section_type,
                        code="duplicate_section_type",
                        message=f"Section type '{section_type}' can only appear once.",
                        path=f"layout.sections.{index}.type",
                    )
                )
            else:
                seen_types[section_type] = section_id
        if errors:
            return errors

    quote_document = document if isinstance(document, QuoteDocumentV1) else QuoteDocumentV1.model_validate(document)
    seen_types: Dict[str, str] = {}

    for index, section in enumerate(quote_document.layout.sections):
        definition = SECTION_REGISTRY.get(section.type)
        path_prefix = f"layout.sections.{index}"
        if definition is None:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="unknown_section_type",
                    message=f"Section type '{section.type}' is not registered.",
                    path=f"{path_prefix}.type",
                )
            )
            continue
        if not definition.allow_multiple and section.type in seen_types:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="duplicate_section_type",
                    message=f"Section type '{section.type}' can only appear once.",
                    path=f"{path_prefix}.type",
                )
            )
        else:
            seen_types[section.type] = section.id
        if not definition.web_anchor or not definition.pdf_anchor:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="missing_renderer_anchor",
                    message=f"Section type '{section.type}' is missing a web/pdf renderer anchor.",
                    path=f"{path_prefix}.type",
                )
            )
        allowed_props = set(definition.props_schema.keys())
        extra_props = sorted(set(section.props.keys()) - allowed_props)
        if extra_props:
            errors.append(
                SectionValidationError(
                    sectionId=section.id,
                    sectionType=section.type,
                    code="invalid_props",
                    message=f"Section type '{section.type}' does not accept props: {', '.join(extra_props)}.",
                    path=f"{path_prefix}.props",
                )
            )
        if not section.enabled:
            continue
        for required_path in definition.required_document_paths:
            if not _path_exists(quote_document, required_path):
                errors.append(
                    SectionValidationError(
                        sectionId=section.id,
                        sectionType=section.type,
                        code="missing_required_document_data",
                        message=f"Section type '{section.type}' requires '{required_path}' to be populated.",
                        path=required_path,
                    )
                )
    return errors

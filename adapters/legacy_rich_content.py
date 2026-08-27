"""Legacy rich content migration and extraction adapters."""

from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict
from schemas.v2.content_blocks import HTML_TAG_RE, _content_text

_LEGACY_HTML_TAG_RE = HTML_TAG_RE
_LEGACY_HTML_ALLOWED_TAGS = {"p", "ul", "ol", "li", "strong", "em", "br", "a"}
LEGACY_RICH_DOCUMENT_FIELDS = ("inclusions", "exclusions", "bookingTerms")


class _LegacyHtmlText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "li", "br"} and self.parts:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def value(self) -> str:
        return "\n".join(line.strip() for line in "".join(self.parts).splitlines() if line.strip()).strip()


def legacy_html_to_plain_text(value: str) -> str:
    """Strict migration-only conversion; unsupported markup is a hard cutoff."""
    for match in HTML_TAG_RE.finditer(value):
        if match.group(1).lower() not in _LEGACY_HTML_ALLOWED_TAGS:
            raise ValueError(f"Unsupported legacy HTML tag <{match.group(1)}>")
    parser = _LegacyHtmlText()
    parser.feed(unescape(value))
    parser.close()
    return parser.value()


def build_rich_content_from_legacy(value: Dict[str, Any]) -> Dict[str, Any]:
    """Migration-only conversion of allowlisted legacy markup."""
    def legacy_plain(item: Any) -> str:
        raw = str(item.get("text") if isinstance(item, dict) else item or "").strip()
        return legacy_html_to_plain_text(raw) if raw else ""

    inclusions = [legacy_plain(item) for item in value.get("inclusions") or []]
    exclusions = [legacy_plain(item) for item in value.get("exclusions") or []]
    terms = value.get("bookingTerms") if isinstance(value.get("bookingTerms"), dict) else {}
    term_items = [
        {"label": str(item.get("label") or item.get("key") or "").strip(), "body": legacy_html_to_plain_text(str(item.get("body") or ""))}
        for item in terms.get("items") or [] if isinstance(item, dict)
    ]
    term_items = [item for item in term_items if item["label"] and item["body"]]
    sections: Dict[str, Any] = {}
    if inclusions or exclusions:
        sections["inclusions_exclusions"] = {"blocks": [{"type": "twoColumnList", "leftTitle": "Inclusions", "leftItems": [item for item in inclusions if item], "rightTitle": "Exclusions", "rightItems": [item for item in exclusions if item]}]}
    booking_blocks: list[dict[str, Any]] = []
    if str(terms.get("description") or "").strip():
        booking_blocks.append({"type": "paragraph", "text": legacy_html_to_plain_text(str(terms.get("description") or ""))})
    if term_items:
        booking_blocks.append({"type": "termList", "items": term_items})
    if booking_blocks:
        sections["booking_terms"] = {"blocks": booking_blocks}
    return {"sections": sections}


def strip_legacy_rich_document_fields(value: Dict[str, Any]) -> Dict[str, Any]:
    """Remove retired rich-content fields after the one-time migration."""
    normalized = dict(value)
    for field in LEGACY_RICH_DOCUMENT_FIELDS:
        normalized.pop(field, None)
    return normalized


def build_rich_content_from_fact_sources(value: Dict[str, Any]) -> Dict[str, Any]:
    """Materialize structured presentation blocks from approved Fact values only."""
    inclusions = [str(item.get("text") if isinstance(item, dict) else item or "").strip() for item in value.get("inclusions") or []]
    exclusions = [str(item.get("text") if isinstance(item, dict) else item or "").strip() for item in value.get("exclusions") or []]
    terms = value.get("bookingTerms") if isinstance(value.get("bookingTerms"), dict) else {}
    boilerplate = value.get("boilerplate") if isinstance(value.get("boilerplate"), dict) else {}
    if not inclusions:
        inclusions = [str(item or "").strip() for item in boilerplate.get("inclusions") or []]
    if not exclusions:
        exclusions = [str(item or "").strip() for item in boilerplate.get("exclusions") or []]
    if not (str(terms.get("description") or "").strip() or terms.get("items")):
        terms = boilerplate.get("booking_terms") if isinstance(boilerplate.get("booking_terms"), dict) else terms

    def plain(value: Any) -> str:
        return _content_text(str(value or ""))

    sections: Dict[str, Any] = {}
    if inclusions or exclusions:
        sections["inclusions_exclusions"] = {"blocks": [{
            "type": "twoColumnList",
            "leftTitle": "Inclusions",
            "leftItems": [plain(item) for item in inclusions if item],
            "rightTitle": "Exclusions",
            "rightItems": [plain(item) for item in exclusions if item],
        }]}

    booking_blocks: list[dict[str, Any]] = []
    if str(terms.get("description") or "").strip():
        booking_blocks.append({"type": "paragraph", "text": plain(terms.get("description"))})
    term_items = [
        {"label": plain(item.get("label") or item.get("key")), "body": plain(item.get("body"))}
        for item in terms.get("items") or []
        if isinstance(item, dict) and (item.get("label") or item.get("key")) and item.get("body")
    ]
    if term_items:
        booking_blocks.append({"type": "termList", "items": term_items})
    if booking_blocks:
        sections["booking_terms"] = {"blocks": booking_blocks}

    return {"sections": sections}


def rich_content_values(document: Any) -> Dict[str, Any]:
    """Extract renderer/legacy projections exclusively from typed blocks."""
    from services.section_registry import QuoteDocumentContentSection
    sections = document.content.sections
    inclusions: list[str] = []
    exclusions: list[str] = []
    for block in sections.get("inclusions_exclusions", QuoteDocumentContentSection()).blocks:
        if block.type == "twoColumnList":
            inclusions.extend(block.leftItems)
            exclusions.extend(block.rightItems)

    booking_description = ""
    booking_items: list[dict[str, str]] = []
    for block in sections.get("booking_terms", QuoteDocumentContentSection()).blocks:
        if block.type == "paragraph" and not booking_description:
            booking_description = block.text
        elif block.type in {"termList", "paymentSchedule"}:
            booking_items.extend({"label": item.label, "body": item.body} for item in block.items)

    return {
        "inclusions": inclusions,
        "exclusions": exclusions,
        "bookingDescription": booking_description,
        "bookingItems": booking_items,
    }

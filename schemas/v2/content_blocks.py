"""Canonical, layout-independent rich content blocks for Quotation V2."""

from html import escape
from html.parser import HTMLParser
import re
from typing import Annotated, Any, List, Literal, Union
from urllib.parse import urlparse
from pydantic import BeforeValidator, ConfigDict, Field, TypeAdapter, field_validator, model_validator
from schemas.quote_document.brand import QuoteBaseModel


class _SafeTermHtml(HTMLParser):
    allowed_tags = {"p", "ul", "ol", "li", "strong", "em", "br", "a"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.allowed_tags:
            return
        if tag != "a":
            self.parts.append(f"<{tag}>")
            return
        href = next((value or "" for name, value in attrs if name == "href"), "")
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https", "mailto"}:
            self.parts.append("<a>")
            return
        self.parts.append(f'<a href="{escape(href, quote=True)}">')

    def handle_endtag(self, tag: str) -> None:
        if tag in self.allowed_tags and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(escape(data))


def sanitize_term_html(value: str) -> str:
    parser = _SafeTermHtml()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)


class QuoteTermItem(QuoteBaseModel):
    id: str
    key: str = ""
    label: str = ""
    body: str = ""

    @field_validator("body")
    @classmethod
    def sanitize_body(cls, value: str) -> str:
        return sanitize_term_html(value)


class _ContentBlockModel(QuoteBaseModel):
    """Base class for the canonical, layout-independent content block union."""

    model_config = ConfigDict(extra="forbid")


HTML_TAG_RE = re.compile(r"</?([a-zA-Z0-9!][a-zA-Z0-9_-]*)(?:\s[^>]*)?>")
_HTML_TAG_RE = HTML_TAG_RE


def _content_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Content text cannot be blank.")
    if len(normalized) > 4000:
        raise ValueError("Content block strings cannot exceed 4,000 characters.")
    if HTML_TAG_RE.search(normalized):
        raise ValueError("Rich content blocks cannot contain HTML.")
    return normalized


ContentText = Annotated[str, BeforeValidator(_content_text), Field(min_length=1, max_length=4000)]


class ParagraphContentBlock(_ContentBlockModel):
    type: Literal["paragraph"]
    text: ContentText


class BulletListContentBlock(_ContentBlockModel):
    type: Literal["bulletList"]
    items: List[ContentText] = Field(min_length=1, max_length=40)


class TwoColumnListContentBlock(_ContentBlockModel):
    type: Literal["twoColumnList"]
    leftTitle: ContentText
    leftItems: List[ContentText] = Field(default_factory=list, max_length=40)
    rightTitle: ContentText
    rightItems: List[ContentText] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def require_a_column_item(self) -> "TwoColumnListContentBlock":
        if not self.leftItems and not self.rightItems:
            raise ValueError("A twoColumnList block requires at least one column item.")
        return self


class TermListItem(_ContentBlockModel):
    label: ContentText
    body: ContentText


class TermListContentBlock(_ContentBlockModel):
    type: Literal["termList"]
    items: List[TermListItem] = Field(min_length=1, max_length=24)


class PaymentScheduleItem(_ContentBlockModel):
    label: ContentText
    body: ContentText


class PaymentScheduleContentBlock(_ContentBlockModel):
    type: Literal["paymentSchedule"]
    items: List[PaymentScheduleItem] = Field(min_length=1, max_length=24)


class CalloutContentBlock(_ContentBlockModel):
    type: Literal["callout"]
    text: ContentText


class ChecklistGroup(_ContentBlockModel):
    title: ContentText
    items: List[ContentText] = Field(min_length=1, max_length=40)


class ChecklistGroupsContentBlock(_ContentBlockModel):
    type: Literal["checklistGroups"]
    groups: List[ChecklistGroup] = Field(min_length=1, max_length=12)


QuoteContentBlock = Annotated[
    Union[
        ParagraphContentBlock,
        BulletListContentBlock,
        TwoColumnListContentBlock,
        TermListContentBlock,
        PaymentScheduleContentBlock,
        CalloutContentBlock,
        ChecklistGroupsContentBlock,
    ],
    Field(discriminator="type"),
]
_QUOTE_CONTENT_BLOCK_ADAPTER = TypeAdapter(QuoteContentBlock)


def validate_quote_content_block(value: Any) -> Any:
    """Validate one canonical block; used for generated, patched, and migrated values."""
    return _QUOTE_CONTENT_BLOCK_ADAPTER.validate_python(value)

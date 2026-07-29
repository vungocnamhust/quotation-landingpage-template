from __future__ import annotations

from typing import Any


class DocumentRevisionConflictError(Exception):
    def __init__(
        self,
        *,
        quotation_id: str,
        lang: str,
        expected_revision: int | None,
        current_revision: int | None,
        current_document: dict[str, Any] | None,
    ) -> None:
        self.quotation_id = quotation_id
        self.lang = lang
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        self.current_document = current_document
        super().__init__(
            f"Document revision conflict for quotation={quotation_id} lang={lang}: "
            f"expected={expected_revision}, current={current_revision}"
        )

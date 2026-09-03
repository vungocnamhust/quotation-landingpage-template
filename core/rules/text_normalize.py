"""Single source of truth for dedupe-key text normalization (15.2 §1.2).

Shared by supplier and product dedupe so the two modules can never drift into
separate algorithms again (Track 1 audit H1/M7).
"""
from __future__ import annotations

import re

from core.rules.destination_rules import remove_diacritics

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(value: str) -> str:
    """lower + strip diacritics (đ/Đ-aware) + collapse whitespace."""
    without_marks = remove_diacritics(value or "")
    return _WHITESPACE_RE.sub(" ", without_marks).strip().lower()

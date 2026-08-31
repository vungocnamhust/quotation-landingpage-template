"""Pure sanitizer for raw ingestion text (15.8). No I/O, no LLM calls.

Strips control/zero-width characters and normalizes Unicode so raw pasted text is safe to
carry through the pipeline and hand to the Extractor agent as an opaque data blob. This
module does NOT interpret, filter, or redact content based on meaning — including text that
reads like an instruction to an AI. That is intentional: the prompt-injection defense for
ingestion is architectural (the Extractor is a 0-tool agent that only ever sees this text as
data, never as instructions with tool-calling power), not a content filter here.
"""
from __future__ import annotations

import unicodedata

MAX_RAW_TEXT_CHARS = 50_000

_ZERO_WIDTH_CHARS = (
    "​"  # zero width space
    "‌"  # zero width non-joiner
    "‍"  # zero width joiner
    "⁠"  # word joiner
    "﻿"  # BOM / zero width no-break space
)
_ZERO_WIDTH_TABLE = str.maketrans("", "", _ZERO_WIDTH_CHARS)

DELIMITER_TAG = "INGESTION_RAW_TEXT"


def _strip_control_chars(text: str) -> str:
    """Drop Unicode category Cc (control) chars, keeping newline and tab for readability."""
    return "".join(ch for ch in text if ch in ("\n", "\t") or unicodedata.category(ch) != "Cc")


def sanitize_ingest_text(raw_text: str | None) -> str:
    """Sanitize raw pasted text before it enters staging or reaches the Extractor agent.

    - Normalize to Unicode NFC.
    - Strip zero-width characters (steganography / token-smuggling defense).
    - Strip C0/C1 control characters (keep newline/tab).
    - Cap length at MAX_RAW_TEXT_CHARS (truncate, never raise).
    """
    if not raw_text:
        return ""
    text = unicodedata.normalize("NFC", raw_text)
    text = text.translate(_ZERO_WIDTH_TABLE)
    text = _strip_control_chars(text)
    return text[:MAX_RAW_TEXT_CHARS]


def wrap_with_delimiter(sanitized_text: str) -> str:
    """Wrap sanitized text in an explicit delimiter block for prompt assembly.

    Marks the untrusted-text boundary for the Extractor prompt template. This is a
    formatting aid for the prompt, not an escaping/filtering mechanism — content inside is
    passed through unchanged, verbatim.
    """
    return f"<{DELIMITER_TAG}>\n{sanitized_text}\n</{DELIMITER_TAG}>"

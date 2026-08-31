"""Runs the ingestion corpus (15.8 §4) through sanitize -> Extractor (real LLM) -> parse and
checks the result against ``manifest.json``'s coarse expectations (15.8 §3).

LLM-dependent — marked ``@pytest.mark.integration`` so it does not run in the default
``pytest`` invocation. Select it explicitly once a provider is configured
(``DEEPSEEK_API_KEY``/``OPENAI_API_KEY``):

    PYTHONPATH=. pytest -m integration tests/test_ingestion_corpus.py

The corpus fixtures under ``tests/fixtures/ingestion_corpus/`` are a SYNTHETIC placeholder
set (see that directory's README.md) — this test proves the harness works, not that the
real, anonymized operator corpus has landed yet.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from core.rules.ingest_sanitizer import sanitize_ingest_text
from services.ingestion.extraction_service import _run_extractor, parse_payload, verify_source_quotes

CORPUS_DIR = Path(__file__).resolve().parent / "fixtures" / "ingestion_corpus"
MANIFEST = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))


async def _extract_and_parse(case: dict):
    raw_text = (CORPUS_DIR / case["file"]).read_text(encoding="utf-8")
    sanitized = sanitize_ingest_text(raw_text)
    extracted = await _run_extractor(sanitized)
    verified = verify_source_quotes(extracted, sanitized)
    return parse_payload(verified)


def _assert_matches_expectations(payload, case: dict) -> None:
    expected = case["expected"]
    if "supplier_present" in expected:
        assert (payload.supplier is not None) == expected["supplier_present"], case["file"]
    if "products_min" in expected:
        assert len(payload.products) >= expected["products_min"], case["file"]
    if "rate_groups_min" in expected:
        assert len(payload.rate_groups) >= expected["rate_groups_min"], case["file"]
    if "unresolved_min" in expected:
        assert len(payload.unresolved) >= expected["unresolved_min"], case["file"]
    if "covers_multiple_suppliers" in expected:
        assert payload.covers_multiple_suppliers == expected["covers_multiple_suppliers"], case["file"]
    if "requires_clarification" in expected:
        needs_clarification = bool(payload.unresolved) or payload.covers_multiple_suppliers
        assert needs_clarification == expected["requires_clarification"], case["file"]


@pytest.mark.integration
@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda c: c["file"])
def test_corpus_case_matches_manifest_expectations(case):
    payload, _parsed = asyncio.run(_extract_and_parse(case))
    _assert_matches_expectations(payload, case)

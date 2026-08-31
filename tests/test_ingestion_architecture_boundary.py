"""Machine-checked architecture invariants for 15.8 (§5 "An toàn kiểm bằng máy").

These are exactly the chốt #1/#2 guarantees the plan calls out as CI-checkable — until now
verified only by ad-hoc ``grep`` during development. Encoding them as tests means a future
change that violates a boundary fails CI instead of relying on someone remembering to grep.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

from core.rules.ingest_parser import (
    parse_amount_text,
    parse_cancellation_policy_text,
    parse_tier_pax_text,
    parse_validity_text,
)
from services.ai_platform.toolsets.catalog import CATALOG_TOOLSET_B
from services.ingestion import commit_service, extraction_service, resolution_service

INGESTION_DIR = Path(extraction_service.__file__).parent
# chốt #1: only commit_service.py (the sole catalog writer) and resolution_service.py
# (read-only dedupe/overlap verification, per the task's own validation criterion) may
# import a catalog model, repository, or service.
CATALOG_IMPORT_ALLOWED_MODULES = {"commit_service.py", "resolution_service.py"}
CATALOG_MODULE_PREFIXES = ("db.models.supplier", "db.models.product", "db.models.rate")
CATALOG_REPOSITORY_PREFIXES = (
    "repositories.supplier_repository",
    "repositories.product_repository",
    "repositories.rate_repository",
    "repositories.destination_repository",
)
CATALOG_SERVICE_PREFIXES = ("services.supplier_service", "services.product_service", "services.rate_service")


def _imported_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
    return modules


def test_only_commit_and_resolution_service_import_catalog_internals():
    """chốt #1 — staging isolation: services/ingestion/ must not reach into the catalog's
    models/repositories/services except in the two files audited to do so on purpose.
    """
    offenders: list[str] = []
    for py_file in sorted(INGESTION_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        modules = _imported_modules(py_file)
        touches_catalog = any(
            module.startswith(CATALOG_MODULE_PREFIXES + CATALOG_REPOSITORY_PREFIXES + CATALOG_SERVICE_PREFIXES)
            for module in modules
        )
        if touches_catalog and py_file.name not in CATALOG_IMPORT_ALLOWED_MODULES:
            offenders.append(py_file.name)
    assert not offenders, f"services/ingestion/ files importing catalog internals outside the allowed set: {offenders}"


def test_resolver_functions_never_take_raw_text():
    """chốt #2 — the Resolver only ever sees the already-parsed payload. Verified by
    function signature: no function in resolution_service.py may declare a parameter whose
    name mentions raw_text.
    """
    offenders: list[str] = []
    for name, func in inspect.getmembers(resolution_service, inspect.iscoroutinefunction):
        for param_name in inspect.signature(func).parameters:
            if "raw_text" in param_name:
                offenders.append(f"{name}({param_name})")
    assert not offenders, f"resolution_service functions that accept raw_text: {offenders}"


def test_extractor_is_built_with_zero_tools():
    """The Extractor is the 0-tool boundary (chốt #2) — verified by inspecting the literal
    ``build_agent(..., tools=())`` call in _run_extractor's source, not by relying on
    pydantic_ai's internal toolset representation (which is not a stable public API).
    """
    source = inspect.getsource(extraction_service._run_extractor)
    assert "tools=()" in source, "_run_extractor must call build_agent with an empty tools tuple"


def test_catalog_toolset_b_has_exactly_the_three_documented_tools():
    names = {tool.__name__ for tool in CATALOG_TOOLSET_B}
    assert names == {"find_supplier", "find_products", "find_active_rates"}


def test_ingest_parser_functions_never_import_llm_client():
    """chốt #3 — the deterministic parser must have zero dependency on any LLM/agent
    machinery; it is pure Python over text the Extractor already transcribed."""
    import core.rules.ingest_parser as parser_module

    modules = _imported_modules(Path(parser_module.__file__))
    forbidden = {m for m in modules if "pydantic_ai" in m or m in ("llm_client", "services.ai_platform.runtime")}
    assert not forbidden, f"ingest_parser.py must not depend on LLM/agent machinery, found: {forbidden}"
    # sanity: the four documented pure functions actually exist and are callable without I/O
    assert callable(parse_amount_text)
    assert callable(parse_validity_text)
    assert callable(parse_cancellation_policy_text)
    assert callable(parse_tier_pax_text)


def test_commit_service_is_the_only_ingestion_module_calling_catalog_write_methods():
    """chốt #7 — commit is the single writer. A source-text check for the three real write
    entrypoints (create_supplier/create_product/create_draft) confirms they appear only in
    commit_service.py within services/ingestion/.
    """
    write_markers = ("create_supplier(", "create_product(", "create_draft(", "supersede(", "activate(")
    offenders: list[str] = []
    for py_file in sorted(INGESTION_DIR.glob("*.py")):
        if py_file.name in ("__init__.py", "commit_service.py"):
            continue
        text = py_file.read_text(encoding="utf-8")
        if any(marker in text for marker in write_markers):
            offenders.append(py_file.name)
    assert not offenders, f"catalog write calls found outside commit_service.py: {offenders}"
    assert commit_service is not None  # keeps the import from being flagged unused

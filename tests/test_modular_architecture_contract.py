"""Structural regression tests for the incremental V2 modularization.

They intentionally validate boundaries rather than an implementation detail so
future moves out of ``main.py`` cannot reintroduce the original hidden cycles.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _top_level_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def test_main_has_no_duplicate_top_level_definitions() -> None:
    names = _top_level_names(ROOT / "main.py")
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    assert duplicates == []


def test_services_do_not_import_asgi_composition_root() -> None:
    violations: list[str] = []
    for path in (ROOT / "services").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(alias.name == "main" for alias in node.names):
                violations.append(str(path.relative_to(ROOT)))
            if isinstance(node, ast.ImportFrom) and node.module == "main":
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_extracted_v2_bundles_are_not_registered_from_main() -> None:
    tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"), filename="main.py")
    route_handlers = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "app"
    }
    assert not {
        "upload_media_asset",
        "list_media_assets",
        "select_media_asset",
        "sync_media_assets",
        "get_workspace_me",
        "list_workspace_quotations",
        "get_workspace_quotation_overview",
    }.intersection(route_handlers)


def test_quote_document_keeps_compatibility_exports_after_schema_split() -> None:
    from quote_document import AssetSelectionResult, BrandContentPolicy, BrandProfile, GenerationStatus, QuoteBaseModel
    from schemas.quote_document.brand import (
        AssetSelectionResult as SplitAssetSelectionResult,
        BrandContentPolicy as SplitBrandContentPolicy,
        BrandProfile as SplitBrandProfile,
        GenerationStatus as SplitGenerationStatus,
        QuoteBaseModel as SplitQuoteBaseModel,
    )

    assert (QuoteBaseModel, BrandContentPolicy, BrandProfile, GenerationStatus, AssetSelectionResult) == (
        SplitQuoteBaseModel,
        SplitBrandContentPolicy,
        SplitBrandProfile,
        SplitGenerationStatus,
        SplitAssetSelectionResult,
    )

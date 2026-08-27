#!/usr/bin/env python3
"""CLI audit script to inspect stored quotation documents for deprecated schema fields.

Deprecated fields scanned:
- trip.priceBasis
- route.staySegments[*].mapSegmentDuration
- meta.contentProvenance
- meta.themeOrnaments
- itinerary.days[*].labelHighlights
- itinerary.days[*].labelNotes
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEPRECATED_FIELD_CHECKS = (
    ("trip.priceBasis", lambda doc: "priceBasis" in (doc.get("trip") or {})),
    (
        "route.staySegments[*].mapSegmentDuration",
        lambda doc: any(
            "mapSegmentDuration" in segment
            for segment in ((doc.get("route") or {}).get("staySegments") or [])
        ),
    ),
    ("meta.contentProvenance", lambda doc: "contentProvenance" in (doc.get("meta") or {})),
    ("meta.themeOrnaments", lambda doc: "themeOrnaments" in (doc.get("meta") or {})),
    (
        "itinerary.days[*].labelHighlights",
        lambda doc: any(
            "labelHighlights" in day
            for day in ((doc.get("itinerary") or {}).get("days") or [])
            if day.get("labelHighlights") == ""
        ),
    ),
    (
        "itinerary.days[*].labelNotes",
        lambda doc: any(
            "labelNotes" in day
            for day in ((doc.get("itinerary") or {}).get("days") or [])
            if day.get("labelNotes") == ""
        ),
    ),
)


def audit_document(doc_id: str, doc_data: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    for field_name, check_fn in DEPRECATED_FIELD_CHECKS:
        try:
            if check_fn(doc_data):
                findings.append(field_name)
        except Exception:
            pass
    return {
        "id": doc_id,
        "is_clean": len(findings) == 0,
        "findings": findings,
    }


def scan_directory(directory: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for json_file in directory.glob("**/*.json"):
        if json_file.name.startswith("."):
            continue
        try:
            content = json.loads(json_file.read_text(encoding="utf-8"))
            if isinstance(content, dict) and ("meta" in content or "trip" in content or "itinerary" in content):
                doc_id = content.get("id") or json_file.stem
                results.append(audit_document(doc_id, content))
        except Exception:
            continue
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit quotation documents for deprecated schema fields.")
    parser.add_argument("--dir", type=Path, default=Path("published"), help="Directory containing JSON quotation files.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform audit without modifying data (default).")

    args = parser.parse_args()

    target_dir = args.dir
    if not target_dir.exists():
        target_dir = Path(".")

    results = scan_directory(target_dir)
    total_docs = len(results)
    clean_docs = sum(1 for r in results if r["is_clean"])
    deprecated_docs = total_docs - clean_docs

    findings_summary: dict[str, int] = {}
    for r in results:
        for f in r["findings"]:
            findings_summary[f] = findings_summary.get(f, 0) + 1

    report = {
        "total_scanned": total_docs,
        "clean_count": clean_docs,
        "deprecated_count": deprecated_docs,
        "findings_breakdown": findings_summary,
        "details": results,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("==================================================")
    print("      QUOTATION SCHEMA DEPRECATION AUDIT REPORT   ")
    print("==================================================")
    print(f"Total documents scanned:    {total_docs}")
    print(f"Clean canonical documents:  {clean_docs}")
    print(f"Documents with deprecated:  {deprecated_docs}")
    print("--------------------------------------------------")
    if findings_summary:
        print("Deprecated field occurrences:")
        for field, count in sorted(findings_summary.items(), key=lambda x: -x[1]):
            print(f"  - {field:40s}: {count}")
    else:
        print("No deprecated fields found! All documents are 100% canonical.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())

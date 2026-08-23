#!/usr/bin/env python3
"""
Script to scan and extract all image URLs used across published quotations.
Scans all .html, .pdf, and .json files in quote-generator/public/published/
(or root published/).

Usage:
    python scripts/extract_published_image_urls.py
    python scripts/extract_published_image_urls.py --output-json extracted_images.json --output-txt images_list.txt
    python scripts/extract_published_image_urls.py --check-exists
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote


# Known image file extensions
IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".svg",
    ".gif",
    ".avif",
    ".bmp",
    ".ico",
    ".tiff",
)

# Regex patterns for extracting images
CSS_URL_PATTERN = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.IGNORECASE)
HTML_SRC_PATTERN = re.compile(
    r"""(?:\bsrc|\bdata-src|\bdata-image|\bdata-hero|\bdata-bg|\bdata-poster|\bposter|\bhref)\s*=\s*['"]([^'"><\n\r]+)['"]""",
    re.IGNORECASE,
)


def clean_url(raw: str) -> str | None:
    if not raw or not isinstance(raw, str):
        return None

    # Filter out multi-line chunks or embedded HTML tags
    if "\n" in raw or "\r" in raw or "<" in raw or ">" in raw or len(raw) > 500:
        return None

    cleaned = raw.strip()
    cleaned = html.unescape(cleaned)
    cleaned = unquote(cleaned)
    cleaned = cleaned.strip().strip("'\"`\\").strip()

    # Filter out empty, javascript, data-uris that are not images, anchor links
    if not cleaned or cleaned.startswith(("#", "javascript:", "mailto:", "tel:")):
        return None
    if cleaned.startswith("data:") and not cleaned.startswith("data:image/"):
        return None

    # Check if URL looks like an image
    lower = cleaned.lower().split("?")[0].split("#")[0]
    has_image_ext = any(lower.endswith(ext) for ext in IMAGE_EXTENSIONS)
    has_image_keyword = any(
        kw in lower
        for kw in (
            "/assets/",
            "/published/",
            "/media/",
            "draft_assets",
            "images.unsplash.com",
            "images.pexels.com",
            "static-maps.yandex.ru",
            "maps.googleapis.com",
        )
    )

    if has_image_ext or has_image_keyword:
        return cleaned

    return None


def extract_images_from_json_data(data: Any, found_urls: set[str]) -> None:
    if isinstance(data, dict):
        for val in data.values():
            extract_images_from_json_data(val, found_urls)
    elif isinstance(data, list):
        for item in data:
            extract_images_from_json_data(item, found_urls)
    elif isinstance(data, str):
        # First test if the string is a single clean URL
        url = clean_url(data)
        if url:
            found_urls.add(url)
        elif "<" in data or "url(" in data:
            # String contains nested HTML/CSS; extract sub-matches
            for sub_url in extract_images_from_text(data):
                found_urls.add(sub_url)


def extract_images_from_text(content: str) -> set[str]:
    urls: set[str] = set()

    # 1. Match CSS url(...)
    for match in CSS_URL_PATTERN.finditer(content):
        url = clean_url(match.group(1))
        if url:
            urls.add(url)

    # 2. Match HTML attributes (src, data-src, etc.)
    for match in HTML_SRC_PATTERN.finditer(content):
        url = clean_url(match.group(1))
        if url:
            urls.add(url)

    # 3. Match embedded JSON blocks
    script_json_pattern = re.compile(
        r"""<script[^>]*type=["']application/json["'][^>]*>(.*?)</script>""",
        re.DOTALL | re.IGNORECASE,
    )
    for match in script_json_pattern.finditer(content):
        json_str = match.group(1).strip()
        try:
            parsed = json.loads(json_str)
            extract_images_from_json_data(parsed, urls)
        except Exception:
            pass

    return urls


def categorize_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return "external"
    if url.startswith("/published/") or "draft_assets" in url:
        return "published_draft_assets"
    if url.startswith("/assets/"):
        return "destination_assets"
    if url.startswith("/media/"):
        return "v2_media"
    return "other_relative"


def check_file_exists_on_disk(url: str, project_root: Path) -> bool:
    if url.startswith("http://") or url.startswith("https://") or url.startswith("data:"):
        return True  # Remote or data URI

    # Strip query params and leading slash
    clean_path = url.split("?")[0].lstrip("/")
    if not clean_path:
        return False

    candidates = [
        project_root / "quote-generator" / "public" / clean_path,
        project_root / clean_path,
    ]
    for c in candidates:
        try:
            if c.exists():
                return True
        except OSError:
            continue
    return False


def scan_published_directory(
    published_dir: Path,
    project_root: Path,
    include_json: bool = True,
    check_exists: bool = False,
) -> dict[str, Any]:
    quotation_results: dict[str, Any] = {}
    all_unique_urls: set[str] = set()
    category_counts: dict[str, int] = defaultdict(int)
    file_type_counts: dict[str, int] = defaultdict(int)
    missing_files: list[dict[str, str]] = []

    if not published_dir.exists():
        print(f"Error: Directory {published_dir} does not exist.", file=sys.stderr)
        return {}

    quotation_folders = [d for d in published_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    for quo_dir in sorted(quotation_folders, key=lambda d: d.name):
        quo_id = quo_dir.name
        quo_files: dict[str, list[str]] = {}

        # Find files (.html, .pdf, .json)
        files_to_scan: list[Path] = []
        for ext in ("*.html", "*.pdf"):
            files_to_scan.extend(quo_dir.glob(ext))
        if include_json:
            files_to_scan.extend(quo_dir.glob("*.json"))

        for file_path in sorted(files_to_scan, key=lambda p: p.name):
            file_name = file_path.name
            file_ext = file_path.suffix.lower()
            file_type_counts[file_ext] += 1

            file_urls: set[str] = set()

            if file_ext == ".json":
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    extract_images_from_json_data(data, file_urls)
                except Exception as e:
                    print(f"Warning: Failed to parse JSON {file_path}: {e}", file=sys.stderr)
            elif file_ext in (".html", ".htm"):
                try:
                    text_content = file_path.read_text(encoding="utf-8")
                    file_urls = extract_images_from_text(text_content)
                except Exception as e:
                    print(f"Warning: Failed to read HTML {file_path}: {e}", file=sys.stderr)
            elif file_ext == ".pdf":
                try:
                    raw_bytes = file_path.read_bytes()
                    raw_text = raw_bytes.decode("latin1", errors="ignore")
                    file_urls = extract_images_from_text(raw_text)
                except Exception as e:
                    print(f"Warning: Failed to read PDF {file_path}: {e}", file=sys.stderr)

            if file_urls:
                sorted_urls = sorted(file_urls)
                quo_files[file_name] = sorted_urls
                all_unique_urls.update(sorted_urls)

                for u in sorted_urls:
                    category = categorize_url(u)
                    category_counts[category] += 1
                    if check_exists and not check_file_exists_on_disk(u, project_root):
                        missing_files.append({"quotation_id": quo_id, "file": file_name, "url": u})

        quotation_results[quo_id] = {
            "files": quo_files,
            "total_images_in_quotation": len(
                {u for urls in quo_files.values() for u in urls}
            ),
        }

    return {
        "summary": {
            "total_quotations_scanned": len(quotation_folders),
            "total_unique_image_urls": len(all_unique_urls),
            "file_type_counts": dict(file_type_counts),
            "category_counts": dict(category_counts),
            "total_missing_local_files": len(missing_files) if check_exists else None,
        },
        "unique_image_urls": sorted(all_unique_urls),
        "quotations": quotation_results,
        "missing_files": missing_files if check_exists else [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract all image URLs from published quotations (.html, .pdf, .json)."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=None,
        help="Path to the published folder. Defaults to quote-generator/public/published.",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional file path to save full results as JSON.",
    )
    parser.add_argument(
        "--output-txt",
        type=str,
        default=None,
        help="Optional file path to save unique image URLs as a flat text file.",
    )
    parser.add_argument(
        "--check-exists",
        action="store_true",
        help="Verify whether local image files exist on disk.",
    )
    parser.add_argument(
        "--no-json-files",
        action="store_true",
        help="Exclude .json files (ctx.json, payload.json) from scanning.",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]

    if args.root:
        published_dir = Path(args.root).resolve()
    else:
        candidate = project_root / "quote-generator" / "public" / "published"
        if candidate.exists():
            published_dir = candidate
        else:
            published_dir = project_root / "published"

    print(f"Scanning directory: {published_dir}")
    print(f"Project root: {project_root}")

    results = scan_published_directory(
        published_dir=published_dir,
        project_root=project_root,
        include_json=not args.no_json_files,
        check_exists=args.check_exists,
    )

    summary = results.get("summary", {})
    print("\n" + "=" * 60)
    print("📊 SCAN SUMMARY")
    print("=" * 60)
    print(f"Total Quotations Scanned: {summary.get('total_quotations_scanned', 0)}")
    print(f"Total Unique Image URLs:  {summary.get('total_unique_image_urls', 0)}")
    print("\nFiles Scanned by Extension:")
    for ext, count in summary.get("file_type_counts", {}).items():
        print(f"  - {ext}: {count} files")

    print("\nImages by Category:")
    for cat, count in summary.get("category_counts", {}).items():
        print(f"  - {cat}: {count} references")

    if args.check_exists:
        missing = results.get("missing_files", [])
        print(f"\nMissing Local Files on Disk: {len(missing)}")
        if missing:
            print("Sample missing files:")
            for m in missing[:10]:
                print(f"  [!] {m['quotation_id']} / {m['file']}: {m['url']}")

    # Save JSON output if requested
    if args.output_json:
        out_path = Path(args.output_json).resolve()
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nSaved JSON results to: {out_path}")

    # Save flat text list if requested
    if args.output_txt:
        out_path = Path(args.output_txt).resolve()
        out_path.write_text("\n".join(results.get("unique_image_urls", [])) + "\n", encoding="utf-8")
        print(f"Saved unique image URLs list to: {out_path}")

    # Sample URLs
    unique_urls = results.get("unique_image_urls", [])
    print(f"\nSample Extracted URLs ({min(15, len(unique_urls))}/{len(unique_urls)}):")
    for u in unique_urls[:15]:
        print(f"  • {u}")
    print("=" * 60)


if __name__ == "__main__":
    main()

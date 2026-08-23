#!/usr/bin/env python3
"""
Script to list and remove unused image files from the published folder
that are not referenced in extracted_images.txt.

Usage:
    # 1. Dry run (list unused images without deleting):
    python scripts/clean_unused_published_images.py

    # 2. Actually delete unused images:
    python scripts/clean_unused_published_images.py --delete

    # 3. Clean both quote-generator/public/published and root published/:
    python scripts/clean_unused_published_images.py --delete --also-clean-root
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote


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


def load_allowed_image_paths(extracted_images_file: Path) -> set[str]:
    """Reads extracted_images.txt and extracts normalized relative paths."""
    if not extracted_images_file.exists():
        print(f"Error: Images file {extracted_images_file} does not exist.", file=sys.stderr)
        sys.exit(1)

    lines = extracted_images_file.read_text(encoding="utf-8").splitlines()
    allowed_paths: set[str] = set()

    for line in lines:
        raw = line.strip().strip("'\"`")
        if not raw or raw.startswith("#"):
            continue

        # Strip URL query and hash
        url_path = raw.split("?")[0].split("#")[0]
        url_path = unquote(url_path).strip()

        # We care about published paths, e.g. /published/quo_.../...
        if url_path.startswith("/published/"):
            rel_from_published = url_path[len("/published/"):]
            allowed_paths.add(os.path.normpath(rel_from_published).lower())
            allowed_paths.add(os.path.normpath(rel_from_published))
        elif "published/" in url_path:
            idx = url_path.find("published/")
            rel_from_published = url_path[idx + len("published/"):]
            allowed_paths.add(os.path.normpath(rel_from_published).lower())
            allowed_paths.add(os.path.normpath(rel_from_published))

    return allowed_paths


def scan_and_clean_published_images(
    published_dir: Path,
    allowed_paths: set[str],
    delete_files: bool = False,
) -> dict[str, Any]:
    if not published_dir.exists():
        print(f"Directory {published_dir} does not exist. Skipping.", file=sys.stderr)
        return {}

    total_images = 0
    retained_images = 0
    unused_images: list[dict[str, Any]] = []
    freed_bytes = 0

    # Walk through published directory
    for root, _dirs, files in os.walk(published_dir):
        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()

            # Only check image files
            if ext not in IMAGE_EXTENSIONS:
                continue

            total_images += 1
            rel_path = os.path.relpath(file_path, published_dir)
            norm_rel_path = os.path.normpath(rel_path)

            # Check if this image is in allowed list
            if norm_rel_path.lower() in allowed_paths or norm_rel_path in allowed_paths:
                retained_images += 1
            else:
                size = file_path.stat().st_size
                freed_bytes += size
                quotation_id = rel_path.split(os.sep)[0] if os.sep in rel_path else "root"
                unused_images.append({
                    "path": file_path,
                    "rel_path": norm_rel_path,
                    "quotation_id": quotation_id,
                    "size_bytes": size,
                })

    # Perform deletion if requested
    deleted_count = 0
    if delete_files:
        for item in unused_images:
            try:
                item["path"].unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete {item['path']}: {e}", file=sys.stderr)

        # Clean empty directories
        for root, dirs, _files in os.walk(published_dir, topdown=False):
            for d in dirs:
                dir_path = Path(root) / d
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                except Exception:
                    pass

    return {
        "published_dir": str(published_dir),
        "total_images_found": total_images,
        "retained_images_count": retained_images,
        "unused_images_count": len(unused_images),
        "deleted_count": deleted_count if delete_files else 0,
        "freed_bytes": freed_bytes,
        "unused_images": unused_images,
    }


def format_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List and clean unused image files in the published folder."
    )
    parser.add_argument(
        "--images-file",
        type=str,
        default=None,
        help="Path to extracted_images.txt. Defaults to extracted_images.txt in repo root.",
    )
    parser.add_argument(
        "--published-dir",
        type=str,
        default=None,
        help="Path to published folder. Defaults to quote-generator/public/published.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete the unused images. Without this flag, only dry-run is performed.",
    )
    parser.add_argument(
        "--also-clean-root",
        action="store_true",
        help="Also clean root published/ directory in addition to quote-generator/public/published.",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]

    # Resolve extracted_images.txt
    if args.images_file:
        images_file = Path(args.images_file).resolve()
    else:
        candidate_1 = project_root / "extracted_images.txt"
        candidate_2 = project_root / "quote-generator" / "public" / "extracted_image_urls.txt"
        if candidate_1.exists():
            images_file = candidate_1
        elif candidate_2.exists():
            images_file = candidate_2
        else:
            print(f"Error: Cannot find extracted_images.txt in {project_root}", file=sys.stderr)
            sys.exit(1)

    print(f"Reading allowed images from: {images_file}")
    allowed_paths = load_allowed_image_paths(images_file)
    print(f"Loaded {len(allowed_paths)} allowed image path patterns from file.\n")

    # Target directories to scan
    target_dirs: list[Path] = []
    if args.published_dir:
        target_dirs.append(Path(args.published_dir).resolve())
    else:
        next_pub = project_root / "quote-generator" / "public" / "published"
        if next_pub.exists():
            target_dirs.append(next_pub)
        if args.also_clean_root:
            root_pub = project_root / "published"
            if root_pub.exists() and root_pub not in target_dirs:
                target_dirs.append(root_pub)

    mode_label = "🔴 LIVE DELETION" if args.delete else "🟡 DRY RUN (No files will be deleted)"
    print("=" * 70)
    print(f"CLEAN UNUSED PUBLISHED IMAGES — {mode_label}")
    print("=" * 70)

    for target_dir in target_dirs:
        print(f"\n📂 Scanning: {target_dir}")
        res = scan_and_clean_published_images(
            published_dir=target_dir,
            allowed_paths=allowed_paths,
            delete_files=args.delete,
        )

        unused = res.get("unused_images", [])
        print(f"  • Total image files found:    {res.get('total_images_found', 0)}")
        print(f"  • Active/retained images:     {res.get('retained_images_count', 0)}")
        print(f"  • Unused/orphaned images:     {len(unused)}")
        print(f"  • Space occupied by unused:   {format_size(res.get('freed_bytes', 0))}")

        if unused:
            print("\n  Listing of Unused Images:")
            by_quote = defaultdict(list)
            for item in unused:
                by_quote[item["quotation_id"]].append(item)

            for quo_id, items in sorted(by_quote.items()):
                print(f"    [{quo_id}] ({len(items)} files):")
                for it in items:
                    status = "DELETED" if args.delete else "ORPHANED"
                    print(f"      - [{status}] {it['rel_path']} ({format_size(it['size_bytes'])})")

        if args.delete:
            print(f"\n  ✅ Successfully deleted {res.get('deleted_count', 0)} unused files ({format_size(res.get('freed_bytes', 0))} freed).")
        else:
            print("\n  💡 Run with `--delete` to permanently remove these unused files.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

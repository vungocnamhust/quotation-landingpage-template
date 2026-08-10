from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.session import get_session_factory
from repositories import MediaRepository, QuotationRepository
from scripts._migration_common import discover_quotation_dirs
from services.media_service import MediaService, MediaValidationError, compute_sha256_bytes
from services.storage.r2_storage import R2Storage


async def migrate_media_to_r2(
    *,
    published_root: str | Path = "published",
    quotation_ids: list[str] | None = None,
    session_factory=None,
    storage: R2Storage | None = None,
) -> dict[str, Any]:
    if session_factory is None:
        session_factory = get_session_factory()
    if storage is None:
        storage = R2Storage()

    media_service = MediaService(storage=storage)
    summary: dict[str, Any] = {
        "scannedQuotations": 0,
        "scannedFiles": 0,
        "uploaded": 0,
        "skipped": 0,
        "failed": 0,
        "skippedQuotations": 0,
        "items": [],
    }

    for quotation_dir in discover_quotation_dirs(published_root, quotation_ids):
        draft_assets_dir = quotation_dir / "draft_assets"
        if not draft_assets_dir.exists() or not draft_assets_dir.is_dir():
            continue

        summary["scannedQuotations"] += 1
        quotation_id = quotation_dir.name
        async with session_factory() as session:
            quotation_repository = QuotationRepository(session)
            media_repository = MediaRepository(session)
            quotation = await quotation_repository.get_quotation_by_id(quotation_id)
            if quotation is None:
                summary["skippedQuotations"] += 1
                summary["items"].append(
                    {
                        "quotationId": quotation_id,
                        "status": "skipped",
                        "reason": "quotation missing from database",
                    }
                )
                continue

            for candidate in sorted(draft_assets_dir.rglob("*")):
                if not candidate.is_file():
                    continue
                summary["scannedFiles"] += 1
                try:
                    content = await asyncio.to_thread(candidate.read_bytes)
                    checksum = await asyncio.to_thread(compute_sha256_bytes, content)
                    existing = await media_repository.get_media_asset_by_checksum(
                        checksum,
                        quotation_id=quotation_id,
                    )
                    if existing is not None:
                        if existing.local_path != str(candidate):
                            existing.local_path = str(candidate)
                            await session.commit()
                        summary["skipped"] += 1
                        summary["items"].append(
                            {
                                "quotationId": quotation_id,
                                "status": "skipped",
                                "assetId": existing.id,
                                "localPath": str(candidate),
                                "reason": "checksum_exists",
                            }
                        )
                        continue

                    created = await media_service.create_media_asset(
                        session,
                        original_filename=candidate.name,
                        content=content,
                        declared_mime_type=None,
                        quotation_id=quotation_id,
                        source_type="migration_draft_asset",
                        local_path=str(candidate),
                        metadata_json={"migrationSource": "published_draft_assets"},
                    )
                    await session.commit()
                    summary["uploaded"] += 1
                    summary["items"].append(
                        {
                            "quotationId": quotation_id,
                            "status": "uploaded",
                            "assetId": created.id,
                            "localPath": str(candidate),
                            "r2Key": created.r2_key,
                        }
                    )
                except MediaValidationError as exc:
                    await session.rollback()
                    summary["failed"] += 1
                    summary["items"].append(
                        {
                            "quotationId": quotation_id,
                            "status": "failed",
                            "localPath": str(candidate),
                            "reason": str(exc),
                        }
                    )
                except Exception as exc:
                    await session.rollback()
                    summary["failed"] += 1
                    summary["items"].append(
                        {
                            "quotationId": quotation_id,
                            "status": "failed",
                            "localPath": str(candidate),
                            "reason": str(exc) or exc.__class__.__name__,
                        }
                    )

    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload legacy published/<quotation>/draft_assets files to R2 and media_assets.")
    parser.add_argument("--published-root", default="published", help="Legacy published root to scan. Defaults to ./published")
    parser.add_argument(
        "--quotation-id",
        action="append",
        dest="quotation_ids",
        default=[],
        help="Limit migration to one or more quotation ids.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary = asyncio.run(
        migrate_media_to_r2(
            published_root=args.published_root,
            quotation_ids=args.quotation_ids or None,
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

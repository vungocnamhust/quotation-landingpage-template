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

import main as app_main
from db.session import get_session_factory
from repositories import PublicationRepository, QuotationDocumentRepository, QuotationRepository
from scripts._migration_common import (
    build_document_from_legacy_payload,
    build_publication_storage_keys,
    discover_quotation_dirs,
    extract_available_langs,
    extract_baseline_lang,
    extract_brand_id,
    extract_customer_name,
    extract_html_sync,
    extract_opportunity_id,
    extract_payload_for_lang,
    extract_stored_quote_document,
    extract_template_name,
    extract_title,
    first_int,
    hydrate_canonical_document,
    load_json_file,
    normalize_document_for_migration,
    parse_publication_candidates,
)
from services.storage.r2_storage import R2Storage


async def migrate_quotation_v2_to_postgres(
    *,
    published_root: str | Path = "published",
    quotation_ids: list[str] | None = None,
    session_factory=None,
    upload_publications: bool = False,
    storage: R2Storage | None = None,
) -> dict[str, Any]:
    if session_factory is None:
        session_factory = get_session_factory()
    if upload_publications and storage is None:
        storage = R2Storage()

    summary: dict[str, Any] = {
        "scanned": 0,
        "migrated": 0,
        "existing": 0,
        "skippedNoDocument": 0,
        "failed": 0,
        "requestSnapshotsCreated": 0,
        "requestSnapshotsSkipped": 0,
        "publicationsCreated": 0,
        "publicationsSkipped": 0,
        "items": [],
    }

    for quotation_dir in discover_quotation_dirs(published_root, quotation_ids):
        summary["scanned"] += 1
        try:
            result = await _migrate_single_quotation(
                session_factory=session_factory,
                quotation_dir=quotation_dir,
                upload_publications=upload_publications,
                storage=storage,
            )
        except Exception as exc:
            summary["failed"] += 1
            summary["items"].append(
                {
                    "quotationId": quotation_dir.name,
                    "status": "failed",
                    "reason": str(exc) or exc.__class__.__name__,
                }
            )
            continue

        status = result.get("status")
        if status == "migrated":
            summary["migrated"] += 1
        elif status == "existing":
            summary["existing"] += 1
        elif status == "skipped_no_document":
            summary["skippedNoDocument"] += 1
        else:
            summary["failed"] += 1

        summary["requestSnapshotsCreated"] += int(result.get("requestSnapshotsCreated") or 0)
        summary["requestSnapshotsSkipped"] += int(result.get("requestSnapshotsSkipped") or 0)
        summary["publicationsCreated"] += int(result.get("publicationsCreated") or 0)
        summary["publicationsSkipped"] += int(result.get("publicationsSkipped") or 0)
        summary["items"].append(result)

    return summary


async def _migrate_single_quotation(
    *,
    session_factory,
    quotation_dir: Path,
    upload_publications: bool,
    storage: R2Storage | None,
) -> dict[str, Any]:
    quotation_id = quotation_dir.name
    ctx_data = load_json_file(quotation_dir / "ctx.json") or {}
    payload_json = load_json_file(quotation_dir / "payload.json")
    request_json = load_json_file(quotation_dir / "create_request_v2.json")
    document_json = load_json_file(quotation_dir / "document.json")
    baseline_lang = extract_baseline_lang(ctx_data, document_json, request_json)
    if not ctx_data.get("baseline_payload") and payload_json:
        ctx_data["baseline_payload"] = payload_json
    available_langs = extract_available_langs(ctx_data, baseline_lang=baseline_lang)
    publication_candidates = parse_publication_candidates(quotation_dir, baseline_lang)
    discovered_current_version = max(
        [candidate.version for candidate in publication_candidates],
        default=first_int((((document_json or {}).get("meta") or {}).get("version")), default=0),
    )
    brand_id = extract_brand_id(ctx_data, document_json, request_json)
    template_name = extract_template_name(ctx_data, document_json, request_json)
    canonical_template_name = (
        template_name
        if app_main._is_brochure_template(template_name)
        else app_main.BROCHURE_TEMPLATE_NAME
    )
    opportunity_id = extract_opportunity_id(ctx_data, document_json, request_json)
    customer_name = extract_customer_name(ctx_data, document_json, request_json)
    title = extract_title(ctx_data, document_json, request_json)
    normalized_documents = _build_documents_for_languages(
        quotation_id=quotation_id,
        ctx_data=ctx_data,
        payload_json=payload_json,
        document_json=document_json,
        baseline_lang=baseline_lang,
        available_langs=available_langs,
        template_name=canonical_template_name,
        brand_id=brand_id,
        publication_candidates=publication_candidates,
        discovered_current_version=discovered_current_version,
    )
    if not normalized_documents:
        return {
            "quotationId": quotation_id,
            "status": "skipped_no_document",
            "reason": "No usable canonical source found in document.json, ctx.json, payload.json, or translations",
            "requestSnapshotsCreated": 0,
            "requestSnapshotsSkipped": 0,
            "publicationsCreated": 0,
            "publicationsSkipped": 0,
        }

    async with session_factory() as session:
        quotation_repository = QuotationRepository(session)
        document_repository = QuotationDocumentRepository(session)
        publication_repository = PublicationRepository(session)

        quotation = await quotation_repository.get_quotation_by_id(quotation_id)
        request_snapshots_created = 0
        request_snapshots_skipped = 0
        created_documents = 0

        request_snapshots_created = 0
        request_snapshots_skipped = 0

        if quotation is None:
            quotation = await quotation_repository.create_quotation(
                quotation_id=quotation_id,
                brand_id=brand_id,
                template_name=canonical_template_name,
                baseline_lang=baseline_lang,
                opportunity_id=opportunity_id,
                customer_name=customer_name,
                title=title,
                status="published" if discovered_current_version > 0 else "draft",
                current_revision=0,
                current_version=discovered_current_version,
            )
        for lang, normalized_document in normalized_documents.items():
            current_document = await document_repository.get_current_document(quotation_id, lang)
            if current_document is not None:
                continue
            lang_version = _latest_version_for_lang(
                publication_candidates,
                lang=lang,
                fallback=discovered_current_version or quotation.current_version or 1,
            )
            saved_document = await document_repository.save_current_document(
                quotation_id=quotation_id,
                lang=lang,
                document_json=normalized_document,
                expected_revision=0,
                html_sync=extract_html_sync(ctx_data, lang=lang),
            )
            canonical_document = hydrate_canonical_document(
                saved_document.document_json,
                quotation_id=quotation_id,
                lang=lang,
                template_name=canonical_template_name,
                brand_id=brand_id,
                opportunity_id=opportunity_id,
                revision=saved_document.revision,
                version=max(lang_version, 1),
            )
            await document_repository.append_document_revision(
                quotation_id=quotation_id,
                lang=lang,
                revision=saved_document.revision,
                document_json=canonical_document,
                change_source="migration",
            )
            created_documents += 1

        status = "migrated" if quotation is None or created_documents > 0 else "existing"

        latest_request = await quotation_repository.get_latest_quotation_request(quotation_id)
        synthesized_request = request_json or _build_request_snapshot_from_migrated_documents(
            quotation_id=quotation_id,
            baseline_lang=baseline_lang,
            normalized_documents=normalized_documents,
        )
        if synthesized_request:
            if latest_request is None:
                await quotation_repository.create_quotation_request(
                    quotation_id=quotation_id,
                    request_json=synthesized_request,
                )
                request_snapshots_created += 1
            else:
                request_snapshots_skipped += 1

        publications_created = 0
        publications_skipped = 0
        uploaded_keys: list[str] = []
        try:
            for candidate in publication_candidates:
                if not upload_publications:
                    publications_skipped += 1
                    continue
                existing_publication = await publication_repository.get_publication(
                    quotation_id=quotation_id,
                    version=candidate.version,
                    lang=candidate.lang,
                )
                if existing_publication is not None:
                    publications_skipped += 1
                    continue

                html_r2_key, pdf_r2_key = build_publication_storage_keys(
                    quotation_id,
                    candidate.lang,
                    candidate.version,
                )
                content = candidate.html_path.read_bytes()
                await asyncio.to_thread(
                    storage.upload_bytes,
                    html_r2_key,
                    content,
                    "text/html; charset=utf-8",
                )
                uploaded_keys.append(html_r2_key)
                pdf_url = None
                if candidate.pdf_path is not None:
                    pdf_content = candidate.pdf_path.read_bytes()
                    await asyncio.to_thread(
                        storage.upload_bytes,
                        pdf_r2_key,
                        pdf_content,
                        "text/html; charset=utf-8",
                    )
                    uploaded_keys.append(pdf_r2_key)
                    pdf_url = storage.build_public_url(pdf_r2_key)
                await publication_repository.create_publication(
                    quotation_id=quotation_id,
                    version=candidate.version,
                    lang=candidate.lang,
                    html_r2_key=html_r2_key,
                    pdf_r2_key=pdf_r2_key if candidate.pdf_path is not None else None,
                    published_url=storage.build_public_url(html_r2_key),
                    pdf_url=pdf_url,
                )
                publications_created += 1

            await session.commit()
        except Exception:
            await session.rollback()
            for key in uploaded_keys:
                try:
                    await asyncio.to_thread(storage.delete_object, key)
                except Exception:
                    continue
            raise

    return {
        "quotationId": quotation_id,
        "status": status,
        "lang": baseline_lang,
        "availableLangs": available_langs,
        "currentVersion": discovered_current_version,
        "documentsCreated": created_documents,
        "requestSnapshotsCreated": request_snapshots_created,
        "requestSnapshotsSkipped": request_snapshots_skipped,
        "publicationsCreated": publications_created,
        "publicationsSkipped": publications_skipped,
    }


def _latest_version_for_lang(candidates, *, lang: str, fallback: int) -> int:
    versions = [candidate.version for candidate in candidates if candidate.lang == lang]
    return max(versions, default=fallback or 1)


def _build_documents_for_languages(
    *,
    quotation_id: str,
    ctx_data: dict[str, Any],
    payload_json: dict[str, Any] | None,
    document_json: dict[str, Any] | None,
    baseline_lang: str,
    available_langs: list[str],
    template_name: str,
    brand_id: str,
    publication_candidates,
    discovered_current_version: int,
) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    stored_baseline_document = None
    if document_json is not None:
        stored_baseline_document = normalize_document_for_migration(
            document_json,
            quotation_id=quotation_id,
            lang=((document_json.get("meta") or {}).get("lang")) or baseline_lang,
            template_name=template_name,
            brand_id=brand_id,
            current_version=discovered_current_version,
        )
        documents[((stored_baseline_document.get("meta") or {}).get("lang")) or baseline_lang] = stored_baseline_document

    for lang in available_langs:
        stored_document = extract_stored_quote_document(ctx_data, lang=lang)
        if stored_document is not None:
            documents[lang] = normalize_document_for_migration(
                stored_document,
                quotation_id=quotation_id,
                lang=lang,
                template_name=template_name,
                brand_id=brand_id,
                current_version=_latest_version_for_lang(
                    publication_candidates,
                    lang=lang,
                    fallback=discovered_current_version,
                ),
            )
            continue

        if lang in documents:
            continue

        payload_dict = extract_payload_for_lang(
            ctx_data,
            lang=lang,
            baseline_lang=baseline_lang,
            fallback_payload=payload_json,
        )
        if payload_dict is None:
            if lang == baseline_lang and stored_baseline_document is not None:
                documents[lang] = stored_baseline_document
            continue

        generated_document = build_document_from_legacy_payload(
            quotation_id=quotation_id,
            lang=lang,
            baseline_lang=baseline_lang,
            ctx_data=ctx_data,
            payload_dict=payload_dict,
            template_name=template_name,
        )
        documents[lang] = normalize_document_for_migration(
            generated_document,
            quotation_id=quotation_id,
            lang=lang,
            template_name=template_name,
            brand_id=brand_id,
            current_version=_latest_version_for_lang(
                publication_candidates,
                lang=lang,
                fallback=discovered_current_version,
            ),
        )

    return documents


def _build_request_snapshot_from_migrated_documents(
    *,
    quotation_id: str,
    baseline_lang: str,
    normalized_documents: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    baseline_document = normalized_documents.get(baseline_lang) or next(iter(normalized_documents.values()), None)
    if baseline_document is None:
        return None
    return app_main._create_quote_request_from_document(baseline_document).model_dump(mode="json")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate legacy quotation v2 folders from published/ into Postgres.")
    parser.add_argument("--published-root", default="published", help="Legacy published root to scan. Defaults to ./published")
    parser.add_argument(
        "--quotation-id",
        action="append",
        dest="quotation_ids",
        default=[],
        help="Limit migration to one or more quotation ids.",
    )
    parser.add_argument(
        "--upload-publications",
        action="store_true",
        help="Upload legacy published HTML artifacts to R2 and create quotation_publications rows.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary = asyncio.run(
        migrate_quotation_v2_to_postgres(
            published_root=args.published_root,
            quotation_ids=args.quotation_ids or None,
            upload_publications=args.upload_publications,
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

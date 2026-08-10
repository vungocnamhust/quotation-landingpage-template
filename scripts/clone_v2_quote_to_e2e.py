"""Clone one V2 quotation into Compose E2E without mutating the source.

Run inside the Compose app container so DATABASE_URL points to the E2E
Postgres/MinIO services.  SOURCE_DATABASE_URL is read-only by convention and
must point to the main database.  The script preserves the quotation ID only
in E2E and copies every canonical-document R2 object before reporting success.
"""
from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable
from typing import Any

import psycopg
from psycopg.rows import dict_row
import boto3


SERIAL_ID_TABLES = {
    "quotation_requests",
    "quotation_documents",
    "quotation_document_revisions",
    "media_library_objects",
}


def _dsn(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")


def _asset_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        own = {value["r2Key"]} if isinstance(value.get("r2Key"), str) and value["r2Key"] else set()
        return own | set().union(*(_asset_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_asset_keys(child) for child in value)) if value else set()
    return set()


def _rows(conn: psycopg.Connection, table: str, where: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT * FROM {table} WHERE {where}", params)
        return list(cur.fetchall())


def _insert_rows(conn: psycopg.Connection, table: str, rows: Iterable[dict[str, Any]]) -> int:
    inserted = 0
    for row in rows:
        payload = dict(row)
        if table in SERIAL_ID_TABLES:
            payload.pop("id", None)
        columns = list(payload)
        placeholders = ", ".join(["%s"] * len(columns))
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                [json.dumps(value) if isinstance(value, (dict, list)) else value for value in payload.values()],
            )
            inserted += cur.rowcount
    return inserted


def _r2_client(prefix: str):
    required = ("ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "BUCKET", "ENDPOINT")
    values = {name: os.getenv(f"{prefix}{name}", "").strip() for name in required}
    absent = [name for name, value in values.items() if not value]
    if absent:
        raise ValueError(f"{prefix} is missing R2 settings: {', '.join(absent)}")
    client = boto3.client(
        "s3",
        endpoint_url=values["ENDPOINT"],
        aws_access_key_id=values["ACCESS_KEY_ID"],
        aws_secret_access_key=values["SECRET_ACCESS_KEY"],
        region_name=os.getenv(f"{prefix}REGION", "us-east-1"),
    )
    return client, values["BUCKET"]


def _copy_r2_objects(keys: set[str]) -> None:
    source, source_bucket = _r2_client("SOURCE_R2_")
    target, target_bucket = _r2_client("R2_")
    for key in sorted(keys):
        source_object = source.get_object(Bucket=source_bucket, Key=key)
        target.put_object(
            Bucket=target_bucket,
            Key=key,
            Body=source_object["Body"].read(),
            ContentType=source_object.get("ContentType") or "application/octet-stream",
        )


def clone_database(*, source_dsn: str, target_dsn: str, quotation_id: str, dry_run: bool) -> dict[str, Any]:
    if _dsn(source_dsn) == _dsn(target_dsn):
        raise ValueError("SOURCE_DATABASE_URL and DATABASE_URL must be different databases.")
    with psycopg.connect(_dsn(source_dsn), row_factory=dict_row, readonly=True) as source:
        quote_rows = _rows(source, "quotations", "id = %s", (quotation_id,))
        if len(quote_rows) != 1:
            raise LookupError(f"Source quotation {quotation_id} was not found.")
        quote = quote_rows[0]
        documents = _rows(source, "quotation_documents", "quotation_id = %s", (quotation_id,))
        if not documents:
            raise LookupError("Source quotation has no canonical document.")
        dependencies: dict[str, list[dict[str, Any]]] = {
            "brands": _rows(source, "brands", "id = %s", (quote["brand_id"],)),
            "travel_designer_profiles": _rows(source, "travel_designer_profiles", "id = %s", (quote["designer_profile_id"],)) if quote.get("designer_profile_id") else [],
            "quotations": quote_rows,
            "quotation_requests": _rows(source, "quotation_requests", "quotation_id = %s", (quotation_id,)),
            "quotation_documents": documents,
            "quotation_document_revisions": _rows(source, "quotation_document_revisions", "quotation_id = %s", (quotation_id,)),
            "quotation_content_drafts": _rows(source, "quotation_content_drafts", "quotation_id = %s", (quotation_id,)),
        }
        keys = set().union(*(_asset_keys(row["document_json"]) for row in documents))
        if quote.get("designer_profile_id"):
            keys.update(key for row in dependencies["travel_designer_profiles"] for key in [row.get("image_r2_key")] if key)
        media_rows = _rows(source, "media_library_objects", "r2_key = ANY(%s)", (list(keys),)) if keys else []
        dependencies["media_library_objects"] = media_rows
    summary = {table: len(rows) for table, rows in dependencies.items()}
    summary["r2Objects"] = len(keys)
    if dry_run:
        return summary
    _copy_r2_objects(keys)
    with psycopg.connect(_dsn(target_dsn)) as target:
        with target.cursor() as cur:
            cur.execute("SELECT id FROM quotations WHERE id = %s", (quotation_id,))
            if cur.fetchone():
                raise ValueError(f"E2E already contains {quotation_id}; refusing to overwrite it.")
        for table in ("brands", "travel_designer_profiles", "quotations", "quotation_requests", "quotation_documents", "quotation_document_revisions", "quotation_content_drafts", "media_library_objects"):
            _insert_rows(target, table, dependencies[table])
        target.commit()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("quotation_id")
    parser.add_argument("--source-dsn", default=os.getenv("SOURCE_DATABASE_URL", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    source_dsn = args.source_dsn.strip()
    target_dsn = os.getenv("DATABASE_URL", "").strip()
    if not source_dsn or not target_dsn:
        raise SystemExit("SOURCE_DATABASE_URL/--source-dsn and DATABASE_URL are required.")
    summary = clone_database(source_dsn=source_dsn, target_dsn=target_dsn, quotation_id=args.quotation_id, dry_run=args.dry_run)
    print(json.dumps({"quotationId": args.quotation_id, "dryRun": args.dry_run, "copied": summary}, sort_keys=True))


if __name__ == "__main__":
    main()

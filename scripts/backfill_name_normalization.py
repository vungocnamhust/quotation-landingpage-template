#!/usr/bin/env python3
"""Backfill supplier.name_normalized / product.title_normalized (Track 1 audit H1).

Recomputes both columns with the unified `core.rules.text_normalize.normalize_name`
(diacritic-aware, including đ/Đ) that replaced two hand-rolled, đ/Đ-blind copies in
services/supplier_service.py and services/product_service.py. Names such as
"Đông Á" and "Dong A" now normalize to the same key, so this can newly surface
duplicate dedupe keys within the same (tenant, destination/category/supplier)
scope that the old normalization never caught.

This script only recomputes the normalized columns and reports collisions; it
never merges, deletes, or renames rows. Resolving a reported collision is a
data decision for an operator, not something to automate here.

Usage:
    PYTHONPATH=. python scripts/backfill_name_normalization.py           # dry run, report only
    PYTHONPATH=. python scripts/backfill_name_normalization.py --apply   # write + report
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict

from sqlalchemy import select

from core.rules.text_normalize import normalize_name
from db.models.product import Product
from db.models.supplier import Supplier
from db.session import get_session_factory


async def _backfill_suppliers(session, *, apply: bool) -> list[str]:
    suppliers = list((await session.scalars(select(Supplier))).all())
    by_key: dict[tuple[str, str], list[Supplier]] = defaultdict(list)
    changed = 0
    for supplier in suppliers:
        new_value = normalize_name(supplier.name)
        if new_value != supplier.name_normalized:
            changed += 1
            if apply:
                supplier.name_normalized = new_value
        by_key[(supplier.tenant_id, new_value)].append(supplier)

    print(f"suppliers: {len(suppliers)} scanned, {changed} name_normalized value(s) changed")
    return _report_collisions("supplier", by_key)


async def _backfill_products(session, *, apply: bool) -> list[str]:
    products = list((await session.scalars(select(Product))).all())
    by_key: dict[tuple, list[Product]] = defaultdict(list)
    changed = 0
    for product in products:
        new_value = normalize_name(product.title)
        if new_value != product.title_normalized:
            changed += 1
            if apply:
                product.title_normalized = new_value
        by_key[
            (
                product.tenant_id,
                product.destination_id,
                product.category,
                new_value,
                product.supplier_id,
                product.origin_destination_id,
            )
        ].append(product)

    print(f"products: {len(products)} scanned, {changed} title_normalized value(s) changed")
    return _report_collisions("product", by_key)


def _report_collisions(label: str, by_key: dict) -> list[str]:
    lines: list[str] = []
    for key, rows in by_key.items():
        if len(rows) < 2:
            continue
        ids = ", ".join(row.id for row in rows)
        lines.append(f"  {label} dedupe-key collision after backfill: key={key!r} ids=[{ids}]")
    if lines:
        print(f"{label}: {len(lines)} post-backfill duplicate-key group(s) found:")
        for line in lines:
            print(line)
    else:
        print(f"{label}: 0 post-backfill duplicate-key groups found")
    return lines


async def main(apply: bool) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        supplier_collisions = await _backfill_suppliers(session, apply=apply)
        product_collisions = await _backfill_products(session, apply=apply)
        if apply:
            await session.commit()
            print("Applied backfill and committed.")
        else:
            await session.rollback()
            print("Dry run only — pass --apply to write changes.")

    total_collisions = len(supplier_collisions) + len(product_collisions)
    print(f"\nTotal post-backfill duplicate-key groups: {total_collisions}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the recomputed values (default: dry run).")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(apply=args.apply)))

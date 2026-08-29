#!/usr/bin/env python3
"""Read-only audit of {province} segment vocabulary in the R2 bucket.

Plan 16.1 M2.2a (docs/plans/refactor-tech-stack/16.1-design-tab-media-resolution.md
§6 Q1): the bucket uses compact province segments (`hanoi`) while
`DestinationCatalog.province_slug` uses hyphenated slugs (`ha-noi`). This
script lists every distinct {province} segment actually present under
`accommodations/{country}/{region}/{province}/...` and under each configured
destination catalog root, so M2.2b can pick compact-normalization or a
bucket migration with real data instead of a guess.

Read-only: only calls S3 ListObjectsV2. Never writes, copies, or deletes.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

from core.config import settings
from core.rules.r2_paths import ACCOMMODATION_ROOT, parse_accommodation_key
from services.storage.r2_storage import R2Storage


def _list_keys(storage: R2Storage, prefix: str) -> list[str]:
    keys: list[str] = []
    paginator = storage.client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=storage.bucket, Prefix=prefix):
        for obj in page.get("Contents", []) or []:
            key = obj.get("Key")
            if key:
                keys.append(key)
    return keys


def audit_accommodation_provinces(storage: R2Storage) -> dict[str, set[str]]:
    """province segment -> set of (country/region) contexts it appears under."""
    by_province: dict[str, set[str]] = defaultdict(set)
    for key in _list_keys(storage, f"{ACCOMMODATION_ROOT}/"):
        parts = parse_accommodation_key(key.split("/"))
        if parts is None:
            continue
        by_province[parts.province].add(f"{parts.country}/{parts.region}")
    return by_province


def audit_destination_roots(storage: R2Storage) -> dict[str, set[str]]:
    """Non-accommodation catalog roots (vietnam/, cambodia/, ...) — list the
    second-level segment under each country root, which is where a
    {province}-shaped folder would live for destination-scenic media."""
    by_root: dict[str, set[str]] = defaultdict(set)
    for root in settings.media_library_country_roots:
        for key in _list_keys(storage, f"{root}/"):
            segments = [s for s in key.split("/") if s]
            # root/{region_or_province}/... — keep the first two segments
            # after the root as raw evidence; the actual grammar for
            # non-accommodation media has never been formally pinned down.
            if len(segments) >= 3:
                by_root[root].add("/".join(segments[1:3]))
    return by_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a text report.")
    args = parser.parse_args()

    storage = R2Storage()
    accommodation_provinces = audit_accommodation_provinces(storage)
    destination_segments = audit_destination_roots(storage)

    compact_like = {p for p in accommodation_provinces if "-" not in p}
    hyphenated_like = {p for p in accommodation_provinces if "-" in p}

    report = {
        "bucket": storage.bucket,
        "accommodationProvinces": {p: sorted(ctx) for p, ctx in sorted(accommodation_provinces.items())},
        "compactFormProvinces": sorted(compact_like),
        "hyphenatedFormProvinces": sorted(hyphenated_like),
        "isConsistentlyCompact": bool(accommodation_provinces) and not hyphenated_like,
        "isConsistentlyHyphenated": bool(accommodation_provinces) and not compact_like,
        "destinationRootSegments": {root: sorted(segs) for root, segs in sorted(destination_segments.items())},
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("=" * 60)
    print("  R2 {province} SEGMENT VOCABULARY AUDIT (read-only)")
    print("=" * 60)
    print(f"Bucket: {report['bucket']}")
    print(f"Accommodation provinces found: {len(accommodation_provinces)}")
    for province, contexts in sorted(accommodation_provinces.items()):
        print(f"  - {province:20s} under {', '.join(contexts)}")
    print("-" * 60)
    print(f"Compact-form (no hyphen):   {sorted(compact_like) or '(none)'}")
    print(f"Hyphenated-form:            {sorted(hyphenated_like) or '(none)'}")
    print(f"Consistently compact:       {report['isConsistentlyCompact']}")
    print(f"Consistently hyphenated:    {report['isConsistentlyHyphenated']}")
    print("-" * 60)
    print("Destination catalog root second-level segments (context only):")
    for root, segs in sorted(destination_segments.items()):
        print(f"  {root}/: {sorted(segs)[:10]}{' ...' if len(segs) > 10 else ''}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

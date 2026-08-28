"""Media asset classification SSOT (Plan 16.1 quyết định #3, R7).

Pure, no I/O. Previously duplicated between `Candidate.classification`
(services/brochure_media_resolver.py) and `main._media_classification` — any
change to the tag vocabulary had to be made in both places or the two silently
diverged. `room` and `ornament` are deliberately absent: `room` never had a
matching category in the confirmed R2 grammar (only `exteriors`/`interiors`
exist), and `ornament` candidates can never occur because `brands/` is not a
catalog root (R8).
"""
from __future__ import annotations

MEDIA_CLASSIFICATION_TAGS: tuple[str, ...] = ("exterior", "interior", "hero")


def classify_media_asset(parent_prefix: str, file_name: str) -> str:
    value = f"{parent_prefix}/{file_name}".lower()
    return next((tag for tag in MEDIA_CLASSIFICATION_TAGS if tag in value), "generic")

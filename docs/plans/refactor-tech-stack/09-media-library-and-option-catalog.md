# 09. Media Library and Option Catalog

R2 taxonomy and upload contract: [11-r2-media-file-contract.md](./11-r2-media-file-contract.md).

## Purpose

Quote Generator separates reusable choices from quotation facts:

- Cloudflare R2 stores image bytes; Postgres indexes allowed media prefixes for fast navigation.
- `media_assets` remains the upload inventory. `media_library_objects` is a read-only index of externally organised R2 objects.
- Brand, template, language and Travel Designer are presentation choices. Destination is resolved against the destination catalog and existing resolver.

## Media library

The library roots are one ordered allowlist: legacy `MEDIA_LIBRARY_PREFIXES`, country roots, `accommodations`, and `team`. The same roots are browsed and scanned by R2 sync; the browser never receives R2 credentials or original-image URLs.

`POST /api/v2/media-library/sync` creates or returns the single active persisted run. It indexes image metadata first, marks objects missing after a completed prefix scan inactive, then creates small JPEG previews with bounded concurrency. Editors can poll the returned run until it is terminal, then reload the indexed browser.

The quotation document stores `QuoteAssetRef.r2Key` as the authoritative identity and may expose a derived URL for rendering. Existing `url`-only assets remain supported.

## Options and destinations

`GET /api/v2/quotation-options` supplies valid brands, compatible templates, supported languages and active Travel Designers. `presentationOptions.templateId` and `presentationOptions.travelDesignerId` are persisted in the request snapshot and resolved into document presentation data.

`GET /api/v2/destinations?query=` seeds/searches `destination_catalog` and aliases generated from `destination_profiles.py`. Facts continue to persist canonical destination strings. `resolvedFacts.destinationRefs` reports the matching ID/slug without making the catalog a new owner of trip facts.

DMC Core retains ownership of DMC trip/service/pricing facts. Quote Generator may still update only `presentation-options` for a DMC quotation.

## UI flow

Facts uses option selects and destination autocomplete/multi-select. Design lazy-loads Media Picker, lets the user navigate R2 prefixes and writes the chosen `r2Key` to canonical document with `baseRevision`. Content drafts do not participate in selection; preview, PDF and publish read only the saved canonical document.
# Published HTML boundary

Media remains R2-backed by `r2Key`. Publication HTML is a separate artifact namespace: `quotations/{id}/publish/{lang}/v{version}/index.html` with immutable caching, plus `current/index.html` with `no-cache`. No PDF artifact is created by the media library or stored in R2.

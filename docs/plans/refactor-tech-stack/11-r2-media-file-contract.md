# 11. R2 Media File Contract

R2 stores image bytes; `media_library_objects` is the searchable index. Quotation documents and Travel Designer profiles persist `r2Key`. `media_assets` and `/api/v2/media/*` remain unchanged legacy subsystems.

## Write taxonomy

> **Corrected per Plan 16.1 R1/M2.10** (docs/plans/refactor-tech-stack/16.1-design-tab-media-resolution.md):
> the grammar below was previously missing the `{exteriors|interiors}` segment for
> accommodations, and claimed a `{file-slug}--{asset-id}.{ext}` naming that the code has
> never written — `services/media_library_service.py::create_library_asset` has always
> named objects `{asset-id}.{ext}` (opaque identity is intentional; see its comment).

```text
{country}/{region}/{province}/{destination}/{asset-id}.{ext}
{country}/{region}/{province}/{destination}/preview/{asset-id}.jpg
accommodations/{country}/{region}/{province}/{accommodation}/{exteriors|interiors}/{asset-id}.{ext}
accommodations/{country}/{region}/{province}/{accommodation}/{exteriors|interiors}/preview/{asset-id}.jpg
team/{user-name}/{asset-id}.{ext}
team/{user-name}/preview/{asset-id}.jpg
```

`{province}` is the hyphenated `DestinationCatalog.province_slug` verbatim (e.g. `ha-noi`),
confirmed against the live bucket by `scripts/audit_r2_province_segments.py` (M2.2a) — the
bucket's destination catalog roots (`vietnam/{region}/{province}/...`) already use this form
consistently (`da-lat`, `mui-ne`, `nha-trang`, ...). `core/rules/r2_paths.py` is the SSOT for
this grammar (`parse_accommodation_key`, `r2_province_segment`) — both the resolver's matcher
and the write path (`services/media_locations.py`) consume it, so they cannot independently
drift. One legacy object predates this convention (`accommodations/vietnam/north/hanoi/...`,
compact form) and has not been migrated — a real production R2 rename needs its own explicit
decision, not a silent side effect of this doc fix.

The API generates every key. `preview` and `published` segments are never selectable originals. Existing `shared/media` and `library/media` remain readable but receive no taxonomy uploads.

## API

- `POST /api/v2/media-library/resolve-location` resolves typed destination, accommodation or team context.
- `POST /api/v2/media-library/uploads` validates JPEG/PNG/WEBP, writes original and preview, indexes immediately and returns `r2Key`.
- `POST /api/v2/media-library/sync` returns one persisted refresh run; `GET /api/v2/media-library/sync/{runId}` reports progress and failure details.
- `GET /api/v2/media-library/children` and `GET /api/v2/media-library/search` browse only the same roots scanned by sync.

All Media Library APIs require editor authentication. Geographic slugs are seeded in code; incomplete mappings return `422 missingInputs`. Sales never send a raw folder path; new quotation creation sends typed presentation selections and the backend validates their `r2Key` against the active index before seeding the canonical document.
# Quotation publication HTML

The only non-media R2 objects in this contract are published HTML snapshots at `quotations/{id}/publish/{lang}/v{version}/index.html` and their `current/index.html` alias. Version objects use `Cache-Control: public, max-age=31536000, immutable`; current aliases use `Cache-Control: no-cache`. PDF is server-rendered and has no R2 key.

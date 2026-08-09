# 11. R2 Media File Contract

R2 stores image bytes; `media_library_objects` is the searchable index. Quotation documents and Travel Designer profiles persist `r2Key`. `media_assets` and `/api/v2/media/*` remain unchanged legacy subsystems.

## Write taxonomy

```text
{country}/{region}/{province}/{destination}/{file-slug}--{asset-id}.{ext}
{country}/{region}/{province}/{destination}/preview/{asset-id}.jpg
accommodations/{country}/{region}/{province}/{accommodation}/{file-slug}--{asset-id}.{ext}
accommodations/{country}/{region}/{province}/{accommodation}/preview/{asset-id}.jpg
team/{user-name}/{file-slug}--{asset-id}.{ext}
team/{user-name}/preview/{asset-id}.jpg
```

The API generates every key. `preview` and `published` segments are never selectable originals. Existing `shared/media` and `library/media` remain readable but receive no taxonomy uploads.

## API

- `POST /api/v2/media-library/resolve-location` resolves typed destination, accommodation or team context.
- `POST /api/v2/media-library/uploads` validates JPEG/PNG/WEBP, writes original and preview, indexes immediately and returns `r2Key`.
- `POST /api/v2/media-library/sync` returns one persisted refresh run; `GET /api/v2/media-library/sync/{runId}` reports progress and failure details.
- `GET /api/v2/media-library/children` and `GET /api/v2/media-library/search` browse only the same roots scanned by sync.

All Media Library APIs require editor authentication. Geographic slugs are seeded in code; incomplete mappings return `422 missingInputs`. Sales never send a raw folder path; new quotation creation sends typed presentation selections and the backend validates their `r2Key` against the active index before seeding the canonical document.
# Quotation publication HTML

The only non-media R2 objects in this contract are published HTML snapshots at `quotations/{id}/publish/{lang}/v{version}/index.html` and their `current/index.html` alias. Version objects use `Cache-Control: public, max-age=31536000, immutable`; current aliases use `Cache-Control: no-cache`. PDF is server-rendered and has no R2 key.

# Ingestion corpus (15.8 §4)

**Status: SYNTHETIC placeholder set, not the real corpus.** The 8 cases here are fictional
(no real supplier names, no real business data) — they exist to prove out the corpus format,
the seeding script, and `test_ingestion_corpus.py` end-to-end. Plan 15.8 requires a **real**,
anonymized corpus (~10 seed emails minimum, growing toward ~30) gathered by the operator from
actual supplier tariff emails — see `15-modular-tour-ops-brainstorm.md` and
`15.8-text-to-catalog-ingestion.md` §4. Replace/extend these files with real, anonymized
cases (supplier names/emails/phone numbers changed, pricing/season/policy structure kept
intact) before running `scripts/seed_catalog_via_ingestion.py` against a real environment.

## Format

- One `.txt` file per case: the raw pasted tariff text, exactly as an operator would paste it.
- `manifest.json` has one entry per file under `cases[]`:
  - `file`: the `.txt` filename.
  - `category_focus`: which taxonomy bucket this case exercises (`accommodation`,
    `transportation`, `guide`, `ticket`, `visa`, or `trap` for an intentionally ambiguous
    case).
  - `expected`: coarse assertions `test_ingestion_corpus.py` checks against the real
    extract→parse output (`products_min`, `rate_groups_min`, `unresolved_min`,
    `requires_clarification`).
  - `scripted_answers`: `{target_path_suffix: answer_value}` — used by
    `scripts/seed_catalog_via_ingestion.py` to auto-answer clarifications during seeding
    (matched by suffix against each outstanding `Clarification.target_path`, not by opaque
    id, since ids are index-based and can shift slightly across LLM runs).

## Why LLM-dependent tests are marked `@pytest.mark.integration`

Extraction requires a real `pydantic_ai` Agent call against a configured LLM provider
(`DEEPSEEK_API_KEY`/`OPENAI_API_KEY`). `test_ingestion_corpus.py` is marked
`@pytest.mark.integration` so it does not run in the default `pytest` invocation and can be
selected deliberately in CI (`pytest -m integration`) once credentials are configured.

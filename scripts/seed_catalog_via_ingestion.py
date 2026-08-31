#!/usr/bin/env python3
"""Seed the catalog by running the ingestion corpus through the REAL 15.8 pipeline (§4).

Not an INSERT script. Every corpus case goes through the exact same path an operator's
browser would use: sanitize -> Extractor (LLM) -> parse -> Resolver (LLM) + deterministic
verification -> bounded Q&A (scripted answers from ``manifest.json``, matched by
``target_path`` suffix) -> commit. This is deliberately the biggest end-to-end test 15.8 has:

- Idempotent by design: re-running the whole corpus a second time must produce 0 new
  catalog records (every batch idempotency key is stable per case file, and
  ``commit_batch``/``create_batch`` both replay on a repeat key).
- The human gate is not bypassed: cases go through the same 2-round clarification cap and
  the same blocking-clarification check as a real operator would — scripted answers just
  play the operator's role for cases the manifest has answers for. A "trap" case without
  enough scripted answers is reported as stopped, never force-committed.

Guarded by ``ALLOW_INGESTION_SEED=1`` so it can never run against production by accident.

Usage:
    ALLOW_INGESTION_SEED=1 python -m scripts.seed_catalog_via_ingestion
    ALLOW_INGESTION_SEED=1 python -m scripts.seed_catalog_via_ingestion --corpus-dir path/to/corpus
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from core.kernel import ActorRef
from db.session import get_session_factory
from services.ingestion import commit_service, extraction_service, resolution_service

SEED_ACTOR = ActorRef(actor_id="seed", actor_type="system")
DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "ingestion_corpus"
MAX_QA_ROUNDS = resolution_service.MAX_QA_ROUNDS


def _require_seed_flag() -> None:
    if os.getenv("ALLOW_INGESTION_SEED", "").strip().lower() not in {"1", "true", "yes"}:
        print(
            "Refusing to run: set ALLOW_INGESTION_SEED=1 explicitly. "
            "This guard exists so this script can never run against production by accident.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _match_answers(clarifications: list[dict], scripted_answers: dict[str, str]) -> dict[str, str]:
    """Match outstanding clarifications to scripted answers by target_path suffix.

    Matched by suffix (e.g. "validity_text", "amount_text") rather than opaque clarification
    id — ids are index-based and can shift slightly across LLM extraction runs, but the field
    name at the end of a target_path is stable.
    """
    answers: dict[str, str] = {}
    for clarification in clarifications:
        target_path = clarification.get("target_path") or ""
        suffix = target_path.rsplit("/", 1)[-1]
        if suffix in scripted_answers:
            answers[clarification["id"]] = scripted_answers[suffix]
    return answers


async def _seed_one_case(session, case: dict, corpus_dir: Path) -> dict:
    case_file = case["file"]
    raw_text = (corpus_dir / case_file).read_text(encoding="utf-8")
    idempotency_key = f"seed:{case_file}"

    batch, payload, parsed, is_replay = await extraction_service.create_batch(
        session,
        raw_text=raw_text,
        source_channel="internal",
        source_document_type="rate_sheet",
        idempotency_key=idempotency_key,
        actor=SEED_ACTOR,
    )
    if not is_replay:
        batch = await resolution_service.run_first_round(session, batch=batch, payload=payload, parsed=parsed, actor=SEED_ACTOR)
        await session.commit()

    scripted_answers = case.get("scripted_answers", {})
    rounds_used = 0
    while batch.status == "needs_clarification" and rounds_used < MAX_QA_ROUNDS:
        clarifications = (batch.resolution_json or {}).get("clarifications", [])
        answers = _match_answers(clarifications, scripted_answers)
        if not answers:
            break  # no scripted answer covers what's outstanding — stop, do not guess
        batch = await resolution_service.answer_clarifications(
            session, batch=batch, answers=answers, actor=SEED_ACTOR, expected_revision=batch.batch_revision
        )
        await session.commit()
        rounds_used += 1

    if batch.status not in ("ready", "draft", "committed"):
        return {"file": case_file, "outcome": batch.status, "note": "stopped for human — insufficient scripted answers (expected for trap cases)"}

    if batch.status == "committed":
        return {"file": case_file, "outcome": "committed", "commit_result": batch.commit_result_json, "replay": True}

    committed = await commit_service.commit_batch(
        session,
        batch=batch,
        actor=SEED_ACTOR,
        expected_revision=batch.batch_revision,
        idempotency_key=f"seed-commit:{case_file}",
        acknowledge_unresolved=True,
    )
    await session.commit()
    return {"file": case_file, "outcome": "committed", "commit_result": committed.commit_result_json, "replay": False}


async def run(corpus_dir: Path) -> list[dict]:
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    session_factory = get_session_factory()
    results: list[dict] = []
    async with session_factory() as session:
        for case in manifest["cases"]:
            try:
                results.append(await _seed_one_case(session, case, corpus_dir))
            except Exception as exc:  # noqa: BLE001 - report and continue with the rest of the corpus
                await session.rollback()
                results.append({"file": case["file"], "outcome": "error", "error": str(exc)})
    return results


def main() -> None:
    _require_seed_flag()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    args = parser.parse_args()

    results = asyncio.run(run(args.corpus_dir))
    committed = [r for r in results if r["outcome"] == "committed"]
    stopped = [r for r in results if r["outcome"] not in ("committed", "error")]
    errored = [r for r in results if r["outcome"] == "error"]

    print(f"Seeded {len(committed)}/{len(results)} case(s) via the real ingestion pipeline.")
    if stopped:
        print(f"{len(stopped)} case(s) stopped for human review (expected for trap cases without enough scripted answers):")
        for r in stopped:
            print(f"  - {r['file']}: {r['outcome']} — {r.get('note', '')}")
    if errored:
        print(f"{len(errored)} case(s) errored:", file=sys.stderr)
        for r in errored:
            print(f"  - {r['file']}: {r['error']}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

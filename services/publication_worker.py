"""Durable single-VPS worker for React PDF publication jobs."""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from core.config import settings
from db.models.publication import PublicationJob
from db.session import get_session_factory
from repositories import PublicationTargetRepository, QuotationRepository
from services.outbox_service import OutboxService
from services.storage.r2_storage import R2Storage
from services.publication_runtime import (
    purge_public_urls,
    release_transition_cache_urls,
    render_react_pdf_bytes,
)


log = logging.getLogger(__name__)


async def _claim_job() -> PublicationJob | None:
    async with get_session_factory()() as session:
        now = datetime.now(timezone.utc)
        expired_lease = now - timedelta(seconds=settings.publication_job_lease_seconds)
        row = await session.scalar(
            select(PublicationJob)
            .where(
                or_(
                    (PublicationJob.status == "queued") & (PublicationJob.next_run_at <= now),
                    (PublicationJob.status == "running") & (PublicationJob.locked_at < expired_lease),
                )
            )
            .order_by(PublicationJob.next_run_at, PublicationJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return None
        row.status = "running"
        row.locked_at = now
        row.locked_by = f"{socket.gethostname()}:{os.getpid()}"
        row.attempts += 1
        await session.commit()
        return row


async def _run_pdf(job: PublicationJob) -> None:
    async with get_session_factory()() as session:
        repository = PublicationTargetRepository(session)
        context = await repository.get_release_context(job.release_id)
        if context is None:
            current = await session.get(PublicationJob, job.id)
            if current is not None:
                current.status, current.last_error = "failed", "Release was removed."
            await session.commit(); return
        brand, target, release = context
        if brand.status != "active" or release.status != "staging":
            job.status, job.last_error = "failed", "Release is no longer publishable."
            await session.commit(); return
    try:
        pdf = await asyncio.to_thread(render_react_pdf_bytes, hostname=brand.hostname, release_id=job.release_id)
        await asyncio.to_thread(R2Storage().upload_bytes, job.artifact_key, pdf, "application/pdf", cache_control="public, max-age=31536000, immutable")
    except Exception as exc:
        async with get_session_factory()() as session:
            current = await session.get(PublicationJob, job.id)
            if current is not None:
                current.last_error = str(exc)[:4000]
                if current.attempts >= current.max_attempts:
                    current.status = "failed"
                    release = await PublicationTargetRepository(session).get_release(current.release_id)
                    if release:
                        release.status = "failed"
                    outbox = OutboxService(session)
                    await outbox.emit_event(
                        event_type="quotation.publication.failed",
                        aggregate_type="quotation",
                        aggregate_id=current.release_id,
                        payload={"error": current.last_error, "release_id": current.release_id},
                    )
                else:
                    current.status = "queued"
                    current.locked_at = None
                    current.locked_by = None
                    current.next_run_at = datetime.now(timezone.utc) + timedelta(
                        seconds=min(
                            settings.publication_job_backoff_max_seconds,
                            settings.publication_job_backoff_base_seconds * (2 ** max(current.attempts - 1, 0)),
                        )
                    )
                await session.commit()
        return
    async with get_session_factory()() as session:
        repository = PublicationTargetRepository(session)
        current = await session.get(PublicationJob, job.id)
        context = await repository.get_release_context(job.release_id)
        if current is None or context is None: return
        _brand, target, release = context
        target = await repository.lock_target_for_update(target.id)
        if target is None:
            current.status, current.last_error = "failed", "Publication target was removed."
            await session.commit()
            return
        release = await repository.get_release(job.release_id)
        if release is None or release.status != "staging":
            current.status, current.last_error = "failed", "Release is no longer staged for activation."
            await session.commit()
            return
        release.pdf_r2_key = current.artifact_key
        previous_release = await repository.activate_release(target=target, release=release)
        quotation = await QuotationRepository(session).get_quotation_by_id(target.quotation_id)
        if quotation:
            quotation.status = "published"; quotation.current_version = max(quotation.current_version, release.release_number)
        current.status = "succeeded"
        current.locked_at = None
        current.locked_by = None
        await repository.create_job(
            release_id=release.id,
            job_type="purge_cache",
            event_key=f"publish-{uuid.uuid4().hex}",
            payload_json={
                "urls": release_transition_cache_urls(
                    hostnames=[_brand.hostname],
                    target=target,
                    releases=[previous_release, release],
                    fallback_hostname=settings.public_fallback_hostname,
                )
            },
            max_attempts=settings.publication_job_max_attempts,
        )

        outbox = OutboxService(session)
        await outbox.emit_event(
            event_type="quotation.publication.completed",
            aggregate_type="quotation",
            aggregate_id=target.quotation_id,
            brand_id=_brand.id,
            payload={
                "title": quotation.title if quotation else f"Quotation {target.quotation_id}",
                "version": quotation.current_version if quotation else release.release_number,
                "designer_profile_id": quotation.designer_profile_id if quotation else None,
                "action_url": f"/workspace/quotations/{target.quotation_id}",
            },
        )
        await outbox.emit_event(
            event_type="quotation.pdf.ready",
            aggregate_type="quotation",
            aggregate_id=target.quotation_id,
            brand_id=_brand.id,
            payload={
                "title": quotation.title if quotation else f"Quotation {target.quotation_id}",
                "designer_profile_id": quotation.designer_profile_id if quotation else None,
                "action_url": f"/workspace/quotations/{target.quotation_id}?tab=pdf",
            },
        )

        await session.commit()


async def _run_cache_purge(job: PublicationJob) -> None:
    async with get_session_factory()() as session:
        repository = PublicationTargetRepository(session)
        current = await session.get(PublicationJob, job.id)
        context = await repository.get_release_context(job.release_id)
        if current is None or context is None:
            return
        brand, target, _release = context
        if not settings.cdn_purge_enabled:
            log.info("CDN purge disabled (cdn_purge_enabled=False); marking job %s succeeded as no-op.", current.id)
            current.status = "succeeded"
            current.locked_at = None
            current.locked_by = None
            await session.commit()
            return
        urls = current.payload_json.get("urls") if isinstance(current.payload_json, dict) else None
        try:
            await purge_public_urls(urls or [f"https://{brand.hostname}/{target.locale}/q/{target.public_slug}"])
        except Exception as exc:
            current.last_error = str(exc)[:4000]
            current.status = "failed" if current.attempts >= current.max_attempts else "queued"
            current.locked_at = None
            current.locked_by = None
            if current.status == "queued":
                current.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=min(settings.publication_job_backoff_max_seconds, settings.publication_job_backoff_base_seconds * (2 ** max(current.attempts - 1, 0))))
            elif current.status == "failed":
                # Terminal purge failure: symmetric with the PDF-render failure
                # branch, which already emits an outbox event on exhaustion.
                await OutboxService(session).emit_event(
                    event_type="quotation.publication.cache_purge_failed",
                    aggregate_type="quotation",
                    aggregate_id=current.release_id,
                    payload={"error": current.last_error, "release_id": current.release_id, "urls": urls or []},
                )
        else:
            current.status = "succeeded"
            current.locked_at = None
            current.locked_by = None
        await session.commit()


async def main() -> None:
    while True:
        try:
            job = await _claim_job()
            if job and job.job_type == "render_pdf":
                await _run_pdf(job)
            elif job and job.job_type == "purge_cache":
                await _run_cache_purge(job)
            else:
                await asyncio.sleep(settings.publication_worker_poll_seconds)
        except Exception:
            # The lease reaper will reclaim a job that could not be finalized.
            # Keep the worker alive so an unrelated malformed job cannot stop
            # all future publications on this VPS.
            log.exception("Publication worker iteration failed; job will be reclaimed after its lease.")
            await asyncio.sleep(settings.publication_worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.brand import Brand
from db.models.publication import PublicationJob, PublicationRelease, PublicationTarget, QuotationPublication
from db.models.quotation import Quotation


class PublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_publication(
        self,
        *,
        quotation_id: str,
        version: int,
        lang: str,
        html_r2_key: str,
        pdf_r2_key: str | None = None,
        published_url: str | None = None,
        pdf_url: str | None = None,
        document_revision: int = 1,
        status: str = "published",
    ) -> QuotationPublication:
        quotation = await self.session.get(Quotation, quotation_id)
        if quotation is None:
            raise ValueError(f"Quotation {quotation_id} not found")

        publication = QuotationPublication(
            quotation_id=quotation_id,
            version=version,
            lang=lang,
            html_r2_key=html_r2_key,
            pdf_r2_key=pdf_r2_key,
            published_url=published_url,
            pdf_url=pdf_url,
            document_revision=document_revision,
            status=status,
        )
        self.session.add(publication)
        quotation.current_version = max(quotation.current_version, version)
        if status == "published":
            quotation.status = "published"
        await self.session.flush()
        return publication

    async def get_current_publication(self, quotation_id: str, *, lang: str) -> QuotationPublication | None:
        return await self.session.scalar(select(QuotationPublication).where(QuotationPublication.quotation_id == quotation_id, QuotationPublication.lang == lang, QuotationPublication.is_current.is_(True)))

    async def mark_current(self, publication: QuotationPublication, *, restored_from_version: int | None = None) -> None:
        await self.session.execute(update(QuotationPublication).where(QuotationPublication.quotation_id == publication.quotation_id, QuotationPublication.lang == publication.lang, QuotationPublication.is_current.is_(True)).values(is_current=False, status="superseded"))
        publication.is_current, publication.status = True, "published"
        publication.restored_from_version = restored_from_version
        quotation = await self.session.get(Quotation, publication.quotation_id)
        if quotation is not None:
            quotation.status = "published"
            quotation.current_version = max(quotation.current_version, publication.version)
        await self.session.flush()

    async def list_publications(
        self,
        quotation_id: str,
        *,
        lang: str | None = None,
        limit: int = 50,
    ) -> list[QuotationPublication]:
        stmt: Select[tuple[QuotationPublication]] = (
            select(QuotationPublication)
            .where(QuotationPublication.quotation_id == quotation_id)
            .order_by(QuotationPublication.version.desc(), QuotationPublication.created_at.desc())
            .limit(limit)
        )
        if lang:
            stmt = stmt.where(QuotationPublication.lang == lang)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_publication(
        self,
        *,
        quotation_id: str,
        version: int,
        lang: str,
    ) -> QuotationPublication | None:
        stmt = (
            select(QuotationPublication)
            .where(QuotationPublication.quotation_id == quotation_id)
            .where(QuotationPublication.version == version)
            .where(QuotationPublication.lang == lang)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PublicationTargetRepository:
    """Owns V2 React-publication targets and immutable releases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_target(self, *, quotation_id: str, brand_id: str, locale: str) -> PublicationTarget | None:
        return await self.session.scalar(
            select(PublicationTarget).where(
                PublicationTarget.quotation_id == quotation_id,
                PublicationTarget.brand_id == brand_id,
                PublicationTarget.locale == locale,
            )
        )

    async def lock_target_for_update(
        self,
        target_id: str,
        *,
        quotation_id: str | None = None,
    ) -> PublicationTarget | None:
        """Serialize every change to a target's release pointer and numbering."""
        statement = select(PublicationTarget).where(PublicationTarget.id == target_id)
        if quotation_id is not None:
            statement = statement.where(PublicationTarget.quotation_id == quotation_id)
        return await self.session.scalar(statement.with_for_update())

    async def _get_target_for_update(
        self,
        *,
        quotation_id: str,
        brand_id: str,
        locale: str,
    ) -> PublicationTarget | None:
        return await self.session.scalar(
            select(PublicationTarget)
            .where(
                PublicationTarget.quotation_id == quotation_id,
                PublicationTarget.brand_id == brand_id,
                PublicationTarget.locale == locale,
            )
            .with_for_update()
        )

    async def get_public_target(self, *, hostname: str, locale: str, slug: str) -> tuple[Brand, PublicationTarget, PublicationRelease] | None:
        stmt = (
            select(Brand, PublicationTarget, PublicationRelease)
            .join(PublicationTarget, PublicationTarget.brand_id == Brand.id)
            .join(PublicationRelease, PublicationRelease.id == PublicationTarget.active_release_id)
            .where(
                Brand.hostname == hostname.lower().rstrip("."),
                Brand.status == "active",
                PublicationTarget.locale == locale,
                PublicationTarget.public_slug == slug,
                PublicationTarget.status == "published",
                PublicationRelease.status == "published",
                PublicationRelease.is_current.is_(True),
            )
        )
        row = (await self.session.execute(stmt)).one_or_none()
        return tuple(row) if row is not None else None

    async def create_or_get_target(
        self, *, quotation_id: str, brand_id: str, locale: str, public_slug: str
    ) -> PublicationTarget:
        target = await self._get_target_for_update(
            quotation_id=quotation_id,
            brand_id=brand_id,
            locale=locale,
        )
        if target is not None:
            return target
        # The advisory lock in publish is the normal serialization path.  The
        # savepoint makes this method safe when a second process reaches the
        # unique target constraint independently.
        for _attempt in range(3):
            try:
                async with self.session.begin_nested():
                    target = PublicationTarget(
                        id=f"pt_{brand_id}_{locale}_{public_slug}",
                        quotation_id=quotation_id,
                        brand_id=brand_id,
                        locale=locale,
                        public_slug=public_slug,
                    )
                    self.session.add(target)
                    await self.session.flush()
                locked_target = await self.lock_target_for_update(target.id)
                if locked_target is not None:
                    return locked_target
            except IntegrityError:
                target = await self._get_target_for_update(
                    quotation_id=quotation_id,
                    brand_id=brand_id,
                    locale=locale,
                )
                if target is not None:
                    return target
        raise RuntimeError("Unable to create or lock publication target after unique-conflict retries.")

    async def create_release(
        self,
        *,
        target: PublicationTarget,
        document_revision: int,
        render_profile_snapshot: dict[str, Any],
        asset_manifest: dict[str, str],
        pdf_r2_key: str | None = None,
    ) -> PublicationRelease:
        locked_target = await self.lock_target_for_update(target.id)
        if locked_target is None:
            raise ValueError("Publication target was not found.")
        for _attempt in range(3):
            latest = await self.session.scalar(
                select(PublicationRelease.release_number)
                .where(PublicationRelease.target_id == locked_target.id)
                .order_by(PublicationRelease.release_number.desc())
                .limit(1)
            )
            next_number = (latest or 0) + 1
            release = PublicationRelease(
                id=f"pr_{locked_target.id[3:]}_{next_number}",
                target_id=locked_target.id,
                release_number=next_number,
                document_revision=document_revision,
                render_profile_snapshot=render_profile_snapshot,
                asset_manifest=asset_manifest,
                pdf_r2_key=pdf_r2_key,
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(release)
                    await self.session.flush()
                return release
            except IntegrityError:
                continue
        raise RuntimeError("Unable to allocate a publication release number after unique-conflict retries.")

    async def activate_release(self, *, target: PublicationTarget, release: PublicationRelease) -> PublicationRelease | None:
        locked_target = await self.lock_target_for_update(target.id)
        if locked_target is None:
            raise ValueError("Publication target was not found.")
        previous = await self.get_release(locked_target.active_release_id) if locked_target.active_release_id else None
        await self.session.execute(
            update(PublicationRelease)
            .where(PublicationRelease.target_id == locked_target.id, PublicationRelease.is_current.is_(True))
            .values(is_current=False, status="superseded")
        )
        release.status = "published"
        release.is_current = True
        release.published_at = datetime.now(timezone.utc)
        locked_target.status = "published"
        locked_target.active_release_id = release.id
        await self.session.flush()
        return previous

    async def restore_release(self, *, target: PublicationTarget, release_number: int) -> tuple[PublicationRelease, PublicationRelease | None] | None:
        locked_target = await self.lock_target_for_update(target.id)
        if locked_target is None:
            return None
        release = await self.session.scalar(
            select(PublicationRelease).where(
                PublicationRelease.target_id == locked_target.id,
                PublicationRelease.release_number == release_number,
                PublicationRelease.status.in_(("published", "superseded")),
            )
        )
        if release is not None:
            previous = await self.activate_release(target=locked_target, release=release)
            return release, previous
        return None

    async def get_release(self, release_id: str) -> PublicationRelease | None:
        return await self.session.get(PublicationRelease, release_id)

    async def get_release_context(self, release_id: str) -> tuple[Brand, PublicationTarget, PublicationRelease] | None:
        row = (await self.session.execute(
            select(Brand, PublicationTarget, PublicationRelease)
            .join(PublicationTarget, PublicationTarget.brand_id == Brand.id)
            .join(PublicationRelease, PublicationRelease.target_id == PublicationTarget.id)
            .where(PublicationRelease.id == release_id)
        )).one_or_none()
        return tuple(row) if row is not None else None

    async def get_public_media_context(self, release_id: str, *, hostname: str) -> tuple[Brand, PublicationTarget, PublicationRelease] | None:
        row = (await self.session.execute(
            select(Brand, PublicationTarget, PublicationRelease)
            .join(PublicationTarget, PublicationTarget.brand_id == Brand.id)
            .join(PublicationRelease, PublicationRelease.target_id == PublicationTarget.id)
            .where(
                PublicationRelease.id == release_id,
                Brand.hostname == hostname.lower().rstrip("."),
                Brand.status == "active",
                PublicationTarget.status == "published",
                PublicationRelease.status.in_(("published", "superseded")),
            )
        )).one_or_none()
        return tuple(row) if row is not None else None

    async def create_pdf_job(self, *, release_id: str, artifact_key: str, max_attempts: int = 5) -> PublicationJob:
        return await self.create_job(
            release_id=release_id,
            job_type="render_pdf",
            event_key="render",
            artifact_key=artifact_key,
            max_attempts=max_attempts,
        )

    async def create_job(
        self,
        *,
        release_id: str,
        job_type: str,
        event_key: str,
        artifact_key: str | None = None,
        payload_json: dict[str, Any] | None = None,
        max_attempts: int = 5,
    ) -> PublicationJob:
        # Release IDs and cache-purge event keys are intentionally opaque and
        # may be long.  Do not concatenate them into the VARCHAR(64) primary
        # key: an overflow here rolls back release activation after PDF render.
        job_identity = f"{release_id}:{job_type}:{event_key}".encode("utf-8")
        job = PublicationJob(
            id=f"pj_{hashlib.sha256(job_identity).hexdigest()[:48]}",
            release_id=release_id,
            job_type=job_type,
            event_key=event_key,
            artifact_key=artifact_key,
            payload_json=payload_json or {},
            max_attempts=max_attempts,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: str) -> PublicationJob | None:
        return await self.session.get(PublicationJob, job_id)

    async def get_latest_job(self, release_id: str) -> PublicationJob | None:
        return await self.session.scalar(
            select(PublicationJob).where(PublicationJob.release_id == release_id).order_by(PublicationJob.created_at.desc()).limit(1)
        )

    async def list_releases(self, target_id: str) -> list[PublicationRelease]:
        result = await self.session.scalars(
            select(PublicationRelease).where(PublicationRelease.target_id == target_id).order_by(PublicationRelease.release_number.desc())
        )
        return list(result.all())

    async def list_public_paths_for_brand(self, brand_id: str) -> list[tuple[str, str]]:
        result = await self.session.execute(
            select(PublicationTarget.locale, PublicationTarget.public_slug).where(
                PublicationTarget.brand_id == brand_id,
                PublicationTarget.status == "published",
            )
        )
        return [(row[0], row[1]) for row in result.all()]

    async def list_active_release_contexts_for_brand(self, brand_id: str) -> list[tuple[PublicationTarget, PublicationRelease]]:
        result = await self.session.execute(
            select(PublicationTarget, PublicationRelease)
            .join(PublicationRelease, PublicationRelease.id == PublicationTarget.active_release_id)
            .where(PublicationTarget.brand_id == brand_id, PublicationTarget.status == "published")
        )
        return [(row[0], row[1]) for row in result.all()]

    async def list_targets(self, quotation_id: str, *, locale: str | None = None) -> list[PublicationTarget]:
        statement = select(PublicationTarget).where(PublicationTarget.quotation_id == quotation_id).order_by(PublicationTarget.created_at.desc())
        if locale:
            statement = statement.where(PublicationTarget.locale == locale)
        result = await self.session.scalars(statement)
        return list(result.all())

    async def get_target_by_id(self, target_id: str, quotation_id: str) -> PublicationTarget | None:
        return await self.session.scalar(select(PublicationTarget).where(PublicationTarget.id == target_id, PublicationTarget.quotation_id == quotation_id))

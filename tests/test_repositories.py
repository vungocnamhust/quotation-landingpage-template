import os
import tempfile
import unittest

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests._db import make_test_engine

from db.base import Base
from db.models.media import MediaSelection
from repositories import (
    DocumentRevisionConflictError,
    MediaRepository,
    PublicationRepository,
    QuotationDocumentRepository,
    QuotationRepository,
)


class RepositoryContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        self.db_file.close()
        self.engine = make_test_engine(f"sqlite+aiosqlite:///{self.db_file.name}")
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        os.unlink(self.db_file.name)

    async def test_create_quotation_and_request_snapshot(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)

            quotation = await quotation_repo.create_quotation(
                quotation_id="quo_repo_1",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
                opportunity_id="opp_1",
                customer_name="Alice",
                title="Vietnam Escape",
            )
            request = await quotation_repo.create_quotation_request(
                quotation_id=quotation.id,
                request_json={"customer": {"name": "Alice"}},
            )
            await session.commit()

        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            saved = await quotation_repo.get_quotation_by_id("quo_repo_1")

            self.assertIsNotNone(saved)
            self.assertEqual(saved.current_revision, 0)
            self.assertEqual(saved.opportunity_id, "opp_1")
            self.assertEqual(request.quotation_id, "quo_repo_1")

    async def test_save_current_document_updates_current_revision_and_appends_snapshot(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            document_repo = QuotationDocumentRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_2",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )

            current = await document_repo.save_current_document(
                quotation_id="quo_repo_2",
                lang="en",
                document_json={"meta": {"quotationId": "quo_repo_2"}, "trip": {"title": "Draft 1"}},
                expected_revision=0,
            )
            await document_repo.append_document_revision(
                quotation_id="quo_repo_2",
                lang="en",
                revision=current.revision,
                document_json=current.document_json,
                change_source="create",
            )
            updated = await document_repo.save_current_document(
                quotation_id="quo_repo_2",
                lang="en",
                document_json={"meta": {"quotationId": "quo_repo_2"}, "trip": {"title": "Draft 2"}},
                expected_revision=1,
            )
            await document_repo.append_document_revision(
                quotation_id="quo_repo_2",
                lang="en",
                revision=updated.revision,
                document_json=updated.document_json,
                change_source="autosave",
            )
            await session.commit()

        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            document_repo = QuotationDocumentRepository(session)
            quotation = await quotation_repo.get_quotation_by_id("quo_repo_2")
            current = await document_repo.get_current_document("quo_repo_2", "en")
            revisions = await document_repo.list_document_revisions("quo_repo_2", lang="en")

            self.assertEqual(quotation.current_revision, 2)
            self.assertEqual(current.revision, 2)
            self.assertEqual(current.document_json["trip"]["title"], "Draft 2")
            self.assertEqual([item.revision for item in revisions], [2, 1])

    async def test_save_current_document_preserves_existing_sync_metadata_when_omitted(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            document_repo = QuotationDocumentRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_metadata",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            created = await document_repo.save_current_document(
                quotation_id="quo_repo_metadata",
                lang="en",
                document_json={"trip": {"title": "Draft 1"}},
                expected_revision=0,
                html_sync={"editedFields": {"tour_title": "Draft 1"}},
                generation_status={"render": "pending"},
            )
            await document_repo.save_current_document(
                quotation_id="quo_repo_metadata",
                lang="en",
                document_json={"trip": {"title": "Draft 2"}},
                expected_revision=created.revision,
            )
            await session.commit()

        async with self.session_factory() as session:
            document_repo = QuotationDocumentRepository(session)
            current = await document_repo.get_current_document("quo_repo_metadata", "en")

            self.assertEqual(current.document_json["trip"]["title"], "Draft 2")
            self.assertEqual(current.html_sync, {"editedFields": {"tour_title": "Draft 1"}})
            self.assertEqual(current.generation_status, {"render": "pending"})

    async def test_save_current_document_raises_conflict_on_stale_revision(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            document_repo = QuotationDocumentRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_3",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await document_repo.save_current_document(
                quotation_id="quo_repo_3",
                lang="en",
                document_json={"trip": {"title": "Draft 1"}},
                expected_revision=0,
            )
            await session.commit()

        async with self.session_factory() as session:
            document_repo = QuotationDocumentRepository(session)
            with self.assertRaises(DocumentRevisionConflictError) as context:
                await document_repo.save_current_document(
                    quotation_id="quo_repo_3",
                    lang="en",
                    document_json={"trip": {"title": "Stale Draft"}},
                    expected_revision=0,
                )

            self.assertEqual(context.exception.current_revision, 1)
            self.assertEqual(context.exception.current_document["trip"]["title"], "Draft 1")

    async def test_concurrent_autosave_allows_only_one_stale_writer_to_succeed(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            document_repo = QuotationDocumentRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_concurrent",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await document_repo.save_current_document(
                quotation_id="quo_repo_concurrent",
                lang="en",
                document_json={"trip": {"title": "Initial Draft"}},
                expected_revision=0,
            )
            await session.commit()

        session1 = self.session_factory()
        session2 = self.session_factory()
        try:
            repo1 = QuotationDocumentRepository(session1)
            repo2 = QuotationDocumentRepository(session2)

            stale_doc_1 = await repo1.get_current_document("quo_repo_concurrent", "en")
            stale_doc_2 = await repo2.get_current_document("quo_repo_concurrent", "en")

            self.assertEqual(stale_doc_1.revision, 1)
            self.assertEqual(stale_doc_2.revision, 1)

            updated = await repo1.save_current_document(
                quotation_id="quo_repo_concurrent",
                lang="en",
                document_json={"trip": {"title": "Writer One"}},
                expected_revision=stale_doc_1.revision,
            )
            await session1.commit()

            with self.assertRaises(DocumentRevisionConflictError) as context:
                await repo2.save_current_document(
                    quotation_id="quo_repo_concurrent",
                    lang="en",
                    document_json={"trip": {"title": "Writer Two"}},
                    expected_revision=stale_doc_2.revision,
                )

            self.assertEqual(updated.revision, 2)
            self.assertEqual(context.exception.current_revision, 2)
            self.assertEqual(context.exception.current_document["trip"]["title"], "Writer One")
            await session2.rollback()
        finally:
            await session1.close()
            await session2.close()

    async def test_media_repository_filters_and_upserts_selection(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            media_repo = MediaRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_4",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await media_repo.create_media_asset(
                asset_id="med_1",
                quotation_id="quo_repo_4",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_4/media/original/med_1.jpg",
                original_filename="halong-bay.jpg",
                mime_type="image/jpeg",
                size_bytes=1024,
                checksum_sha256="abc123",
                source_type="editor_upload",
                metadata_json={"tag": "hero"},
            )
            await media_repo.create_media_asset(
                asset_id="med_2",
                quotation_id="quo_repo_4",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_4/media/original/med_2.jpg",
                original_filename="sapa.jpg",
                mime_type="image/jpeg",
                size_bytes=2048,
                checksum_sha256="def456",
                source_type="vps_sync",
                status="processing",
            )
            first_selection = await media_repo.upsert_media_selection(
                quotation_id="quo_repo_4",
                asset_id="med_1",
                lang="en",
                section_key="hero",
                slot_key="cover_image",
                display_order=0,
            )
            second_selection = await media_repo.upsert_media_selection(
                quotation_id="quo_repo_4",
                asset_id="med_2",
                lang="en",
                section_key="hero",
                slot_key="cover_image",
                display_order=0,
            )
            await session.commit()

        async with self.session_factory() as session:
            media_repo = MediaRepository(session)
            ready_assets = await media_repo.list_media_assets(
                quotation_id="quo_repo_4",
                status="ready",
                search="halong",
            )
            selections = await media_repo.list_media_selections(
                quotation_id="quo_repo_4",
                lang="en",
                section_key="hero",
            )
            checksum_match = await media_repo.get_media_asset_by_checksum("def456", quotation_id="quo_repo_4")

            self.assertEqual([asset.id for asset in ready_assets], ["med_1"])
            self.assertEqual(first_selection.id, second_selection.id)
            self.assertEqual(selections[0].asset_id, "med_2")
            self.assertEqual(checksum_match.id, "med_2")

    async def test_get_media_asset_by_checksum_returns_latest_match_when_duplicates_exist(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            media_repo = MediaRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_checksum",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await media_repo.create_media_asset(
                asset_id="med_dup_1",
                quotation_id="quo_repo_checksum",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_checksum/media/original/med_dup_1.jpg",
                original_filename="halong-1.jpg",
                mime_type="image/jpeg",
                size_bytes=100,
                checksum_sha256="same-checksum",
                source_type="editor_upload",
            )
            await media_repo.create_media_asset(
                asset_id="med_dup_2",
                quotation_id="quo_repo_checksum",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_checksum/media/original/med_dup_2.jpg",
                original_filename="halong-2.jpg",
                mime_type="image/jpeg",
                size_bytes=101,
                checksum_sha256="same-checksum",
                source_type="editor_upload",
            )
            await session.commit()

        async with self.session_factory() as session:
            media_repo = MediaRepository(session)
            latest = await media_repo.get_media_asset_by_checksum(
                "same-checksum",
                quotation_id="quo_repo_checksum",
            )

            self.assertIsNotNone(latest)
            self.assertEqual(latest.id, "med_dup_2")

    async def test_list_media_assets_for_quotation_includes_shared_inventory(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            media_repo = MediaRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_shared_inventory",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await quotation_repo.create_quotation(
                quotation_id="quo_other_inventory",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await media_repo.create_media_asset(
                asset_id="med_quote_only",
                quotation_id="quo_repo_shared_inventory",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_shared_inventory/media/original/med_quote_only.jpg",
                original_filename="quote-only.jpg",
                mime_type="image/jpeg",
                size_bytes=512,
                checksum_sha256="quote-only",
                source_type="editor_upload",
            )
            await media_repo.create_media_asset(
                asset_id="med_shared_only",
                quotation_id=None,
                bucket="quotation-v2",
                r2_key="shared/media/original/med_shared_only.jpg",
                original_filename="shared-only.jpg",
                mime_type="image/jpeg",
                size_bytes=512,
                checksum_sha256="shared-only",
                source_type="local_sync",
            )
            await media_repo.create_media_asset(
                asset_id="med_other_quote",
                quotation_id="quo_other_inventory",
                bucket="quotation-v2",
                r2_key="quotations/quo_other_inventory/media/original/med_other_quote.jpg",
                original_filename="other-quote.jpg",
                mime_type="image/jpeg",
                size_bytes=512,
                checksum_sha256="other-quote",
                source_type="editor_upload",
            )
            await session.commit()

        async with self.session_factory() as session:
            media_repo = MediaRepository(session)
            assets = await media_repo.list_media_assets(quotation_id="quo_repo_shared_inventory")

            self.assertEqual({asset.id for asset in assets}, {"med_quote_only", "med_shared_only"})

    async def test_shared_media_selection_uniqueness_blocks_duplicate_null_lang_rows(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            media_repo = MediaRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_shared",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await media_repo.create_media_asset(
                asset_id="med_shared_1",
                quotation_id="quo_repo_shared",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_shared/media/original/med_shared_1.jpg",
                original_filename="shared-1.jpg",
                mime_type="image/jpeg",
                size_bytes=200,
                checksum_sha256="shared-a",
                source_type="editor_upload",
            )
            await media_repo.create_media_asset(
                asset_id="med_shared_2",
                quotation_id="quo_repo_shared",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_shared/media/original/med_shared_2.jpg",
                original_filename="shared-2.jpg",
                mime_type="image/jpeg",
                size_bytes=201,
                checksum_sha256="shared-b",
                source_type="editor_upload",
            )
            session.add(
                MediaSelection(
                    quotation_id="quo_repo_shared",
                    asset_id="med_shared_1",
                    lang=None,
                    section_key="hero",
                    slot_key="cover_image",
                    display_order=0,
                )
            )
            await session.flush()

            session.add(
                MediaSelection(
                    quotation_id="quo_repo_shared",
                    asset_id="med_shared_2",
                    lang=None,
                    section_key="hero",
                    slot_key="cover_image",
                    display_order=0,
                )
            )
            with self.assertRaises(IntegrityError):
                await session.flush()
            await session.rollback()

    async def test_upsert_media_selection_normalizes_shared_lang_to_all_and_updates_legacy_null_row(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            media_repo = MediaRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_shared_upsert",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            await media_repo.create_media_asset(
                asset_id="med_shared_existing",
                quotation_id="quo_repo_shared_upsert",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_shared_upsert/media/original/med_shared_existing.jpg",
                original_filename="shared-existing.jpg",
                mime_type="image/jpeg",
                size_bytes=200,
                checksum_sha256="shared-existing",
                source_type="editor_upload",
            )
            await media_repo.create_media_asset(
                asset_id="med_shared_replacement",
                quotation_id="quo_repo_shared_upsert",
                bucket="quotation-v2",
                r2_key="quotations/quo_repo_shared_upsert/media/original/med_shared_replacement.jpg",
                original_filename="shared-replacement.jpg",
                mime_type="image/jpeg",
                size_bytes=201,
                checksum_sha256="shared-replacement",
                source_type="editor_upload",
            )
            session.add(
                MediaSelection(
                    quotation_id="quo_repo_shared_upsert",
                    asset_id="med_shared_existing",
                    lang=None,
                    section_key="hero",
                    slot_key="cover_image",
                    display_order=0,
                )
            )
            await session.flush()

            selection = await media_repo.upsert_media_selection(
                quotation_id="quo_repo_shared_upsert",
                asset_id="med_shared_replacement",
                lang=None,
                section_key="hero",
                slot_key="cover_image",
                display_order=0,
            )
            await session.commit()

        async with self.session_factory() as session:
            media_repo = MediaRepository(session)
            shared = await media_repo.list_media_selections(
                quotation_id="quo_repo_shared_upsert",
                lang="all",
                section_key="hero",
                slot_key="cover_image",
            )

            self.assertEqual(selection.lang, "all")
            self.assertEqual(len(shared), 1)
            self.assertEqual(shared[0].asset_id, "med_shared_replacement")
            self.assertEqual(shared[0].lang, "all")

    async def test_create_publication_updates_quotation_status_and_version(self):
        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            publication_repo = PublicationRepository(session)
            await quotation_repo.create_quotation(
                quotation_id="quo_repo_5",
                brand_id="vietnam_safar",
                template_name="brochure",
                baseline_lang="en",
            )
            publication = await publication_repo.create_publication(
                quotation_id="quo_repo_5",
                version=3,
                lang="en",
                html_r2_key="quotations/quo_repo_5/publish/en/v3.html",
                pdf_r2_key="quotations/quo_repo_5/publish/en/v3.pdf",
                published_url="https://cdn.example.com/quo_repo_5/v3.html",
                pdf_url="https://cdn.example.com/quo_repo_5/v3.pdf",
            )
            await session.commit()

        async with self.session_factory() as session:
            quotation_repo = QuotationRepository(session)
            publication_repo = PublicationRepository(session)
            quotation = await quotation_repo.get_quotation_by_id("quo_repo_5")
            publications = await publication_repo.list_publications("quo_repo_5")
            fetched = await publication_repo.get_publication(quotation_id="quo_repo_5", version=3, lang="en")

            self.assertEqual(publication.version, 3)
            self.assertEqual(quotation.status, "published")
            self.assertEqual(quotation.current_version, 3)
            self.assertEqual(publications[0].html_r2_key, "quotations/quo_repo_5/publish/en/v3.html")
            self.assertEqual(fetched.pdf_url, "https://cdn.example.com/quo_repo_5/v3.pdf")


if __name__ == "__main__":
    unittest.main()

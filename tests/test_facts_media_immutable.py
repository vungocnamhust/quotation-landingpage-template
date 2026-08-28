"""Plan 16.1 D2 — media is carved out of the immutable-facts rule.

`PUT /facts/media` must succeed on a business quotation version
(`quotation_family_id` set), while `PUT /facts` and `PUT /facts/designer`
must keep rejecting with 409 `immutable_facts`.
"""
from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch

import main as app_main
from core.auth import Principal
from db.base import Base
from quote_document import CreateQuoteRequestV1
from repositories.destination_repository import DestinationRepository
from repositories.quotation_repository import QuotationDocumentRepository, QuotationRepository
from repositories.travel_designer_repository import TravelDesignerRepository
from routers.v2.quotation_facts import (
    FactsDesignerRequest,
    FactsMediaRequest,
    put_quotation_fact_designer_v2,
    put_quotation_fact_media_v2,
    put_quotation_facts_v2,
)
from services.skeleton_builder import SkeletonBuilder

USER_PAYLOAD = {
    "source": {"kind": "manual", "handoff_id": None},
    "brand_id": "selvara",
    "lang": "en",
    "presentation_options": {
        "template_id": "itinerary-imagery-v1",
        "travel_designer_id": "td_b49deb4d9586",
        "renderer": "quote-generator",
        "theme_id": "brochure",
        "layout_version": 1,
    },
    "trip_facts": {
        "destinations": ["Ho Chi Minh City"],
        "start_date": "2026-09-26",
        "end_date": "2026-09-27",
        "duration_days": 2,
        "duration_nights": 1,
        "itinerary": [
            {
                "id": "day_1_2hd0d43",
                "day_number": 1,
                "destination": "Ho Chi Minh City",
                "summary": "City tour",
                "overnight": "Ho Chi Minh City",
                "meals": ["Breakfast"],
                "highlights": [],
                "notes": [],
                "sense_of_pace": "balanced",
                "display_date": "Sat 26 Sept",
            },
        ],
    },
    "customer_facts": {
        "customer_name": "nam vu",
        "adults": 2,
        "children": 0,
        "nationality": "Vietnam",
        "market": "Vietnam",
    },
    "service_facts": {"hotels": [], "inclusions": [], "exclusions": []},
    "pricing_facts": {
        "options": [
            {
                "id": "opt-standard",
                "label": "Standard",
                "currency": "USD",
                "per_traveler_amount_minor": 50909,
                "group_total_amount_minor": 700000,
                "per_adult_amount_minor": 50909,
                "per_child_amount_minor": None,
            }
        ]
    },
    "booking_facts": {"title": "Journey for nam vu", "description": "Custom journey.", "items": []},
    "designer_facts": {},
    "opportunity_id": "req_immutable_media_test",
    "factMediaSlots": [],
    "content_overrides": {},
    "asset_overrides": {},
    "generation_options": {},
    "retrieval_refs": [],
}


@pytest.mark.anyio
async def test_facts_media_bypasses_immutable_facts_while_facts_and_designer_stay_blocked():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    with patch("main._get_db_session_factory", return_value=factory), \
         patch("routers.v2.quotation_facts._get_helpers", return_value=app_main), \
         patch("main.require_owned_quotation", return_value=None), \
         patch("main._require_active_media_overrides", return_value=None):

        async with factory() as session:
            await DestinationRepository(session).upsert(
                destination_id="dst_ho-chi-minh",
                canonical_name="Ho Chi Minh City",
                slug="ho-chi-minh",
                aliases=["ho chi minh city"],
                country_slug="vietnam",
                region_slug="south",
                province_slug="ho-chi-minh",
                latitude=10.8231,
                longitude=106.6297,
            )
            await TravelDesignerRepository(session).create_profile(
                profile_id="td_b49deb4d9586",
                name="Nam Designer",
                email="nam@example.com",
                phone="+84123456789",
            )
            quotes = QuotationRepository(session)
            documents = QuotationDocumentRepository(session)
            await quotes.create_quotation(
                quotation_id="quo_immutable_media",
                opportunity_id="req_immutable_media_test",
                brand_id="selvara",
                template_name="quote-generator",
                baseline_lang="en",
                customer_name="nam vu",
                title="Journey for nam vu",
                status="draft",
                source_kind="manual",
                source_snapshot_at=datetime.now().astimezone(),
                designer_profile_id="td_b49deb4d9586",
                created_by_profile_id="td_b49deb4d9586",
                quotation_family_id="fam_test",
                business_version=1,
            )
            req = CreateQuoteRequestV1.model_validate(USER_PAYLOAD)
            canonical, resolved = await app_main._resolve_v2_facts(req)
            doc = SkeletonBuilder().build(
                quotation_id="quo_immutable_media",
                payload=canonical,
                resolved_facts=resolved,
                template="quote-generator",
            )
            doc["meta"]["revision"] = 1
            await documents.save_current_document(
                quotation_id="quo_immutable_media",
                lang="en",
                document_json=doc,
                expected_revision=0,
            )
            await quotes.create_quotation_request(
                quotation_id="quo_immutable_media",
                request_json=canonical.model_dump(mode="json"),
            )
            await session.commit()

        principal = Principal(email="test@example.com", role="editor")

        # PUT /facts must stay blocked for a business quotation version.
        with pytest.raises(HTTPException) as facts_exc:
            await put_quotation_facts_v2(
                quotation_id="quo_immutable_media",
                payload=req,
                baseRevision=1,
                principal=principal,
            )
        assert facts_exc.value.status_code == 409
        assert facts_exc.value.detail["code"] == "immutable_facts"

        # PUT /facts/designer must stay blocked too.
        with pytest.raises(HTTPException) as designer_exc:
            await put_quotation_fact_designer_v2(
                quotation_id="quo_immutable_media",
                payload=FactsDesignerRequest(baseRevision=1, designerProfileId="td_b49deb4d9586"),
                principal=principal,
            )
        assert designer_exc.value.status_code == 409
        assert designer_exc.value.detail["code"] == "immutable_facts"

        # PUT /facts/media must NOT be blocked (Plan 16.1 D2 carve-out).
        result = await put_quotation_fact_media_v2(
            quotation_id="quo_immutable_media",
            payload=FactsMediaRequest(
                baseRevision=1,
                slots=[{"fieldId": "assets.hero", "value": {"r2Key": "shared/media/hero.jpg", "altText": ""}}],
            ),
            principal=principal,
        )
        assert result["ok"] is True
        assert result["currentRevision"] == 2
        assert result["document"]["assets"]["hero"]["r2Key"] == "shared/media/hero.jpg"

    await engine.dispose()

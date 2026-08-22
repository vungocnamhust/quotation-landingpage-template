import asyncio
import json
import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models.destination import DestinationCatalog
from services.media_locations import destination_default_media_prefix, destination_location
from quote_document import CreateQuoteRequestV1, QuoteDocumentV1
from repositories.quotation_repository import QuotationRepository, QuotationDocumentRepository, ContentDraftRepository
from repositories.travel_designer_repository import TravelDesignerRepository
from repositories.destination_repository import DestinationRepository
from routers.v2.quotation_facts import put_quotation_facts_v2
from core.auth import Principal
from fastapi import HTTPException
from datetime import datetime
import main as app_main


USER_PAYLOAD = {
  "source": {"kind": "manual", "handoff_id": None},
  "brand_id": "selvara",
  "lang": "en",
  "presentation_options": {
    "template_id": "itinerary-imagery-v1",
    "travel_designer_id": "td_b49deb4d9586",
    "renderer": "quote-generator",
    "theme_id": "brochure",
    "layout_version": 1
  },
  "trip_facts": {
    "destinations": ["Ho Chi Minh City"],
    "start_date": "2026-09-26",
    "end_date": "2026-09-28",
    "duration_days": 3,
    "duration_nights": 2,
    "itinerary": [
      {
        "id": "day_1_2hd0d43",
        "day_number": 1,
        "destination": "Ho Chi Minh City",
        "summary": "THam quan nhà thờ đức bà, bưu điện sài gòn, dinh độc lập",
        "overnight": "Ho Chi Minh City",
        "meals": ["Breakfast"],
        "highlights": [],
        "notes": [],
        "sense_of_pace": "balanced",
        "display_date": "Sat 26 Sept"
      },
      {
        "id": "day_2_wdnpjea",
        "day_number": 2,
        "destination": "Ho Chi Minh City",
        "summary": "Chèo thuyền thúng",
        "overnight": "Ho Chi Minh City",
        "meals": ["Breakfast"],
        "highlights": [],
        "notes": [],
        "sense_of_pace": "balanced",
        "display_date": "Sun 27 Sept"
      },
      {
        "id": "day_3_zsuvpvr",
        "day_number": 3,
        "destination": "Ho Chi Minh City",
        "summary": "Departure day",
        "overnight": "Ho Chi Minh City",
        "meals": ["Breakfast"],
        "highlights": [],
        "notes": [],
        "sense_of_pace": "balanced",
        "display_date": "Mon 28 Sept"
      }
    ],
    "special_requirements": [
      "balcony view room",
      "Dietary: severe nut allergy",
      "Halal/Prayer: alcohol free",
      "Mobility: wheelchair assistant",
      "Health: altitude sensitive"
    ],
    "display_route_text": "Ho Chi Minh City",
    "display_travel_dates": None
  },
  "customer_facts": {
    "customer_name": "nam vu",
    "adults": 10,
    "children": 5,
    "nationality": "Vietnam",
    "guest_profile": "Culinary & Craft",
    "travel_style": "Culinary & Craft",
    "market": "Vietnam",
    "party_label": "10 Adults, 5 children (ages 6, 6, 6, 6, 6)",
    "greeting_name": "nam vu"
  },
  "service_facts": {
    "hotels": [
      {
        "accommodation_id": "acc_ho-chi-minh_cicilia_saigon",
        "destination": "Ho Chi Minh City",
        "name": "Cicilia Saigon Center",
        "room_type": "Standard Room",
        "check_in": "2026-09-26",
        "check_out": "2026-09-27",
        "intro": "Breakfast included.",
        "phone": None,
        "display_city": "Ho Chi Minh City",
        "display_date": "Sat 26 Sept – Sun 27 Sept",
        "hotel_asset": None,
        "room_asset": None
      },
      {
        "accommodation_id": "acc_ho-chi-minh_liberty_central_saigon_riverside_hotel",
        "destination": "Ho Chi Minh City",
        "name": "Liberty Central Saigon Riverside Hotel",
        "room_type": "Standard Room",
        "check_in": "2026-09-27",
        "check_out": "2026-09-28",
        "intro": "Breakfast included.",
        "phone": None,
        "display_city": "Ho Chi Minh City",
        "display_date": "Sun 27 Sept – Mon 28 Sept",
        "hotel_asset": None,
        "room_asset": None
      }
    ],
    "inclusions": [
      "Airport transfer and arrival greeting",
      "Private vehicle transfers (7-seat SUV)",
      "Full-trip private English-speaking tour director/guide",
      "Domestic flights as specified in the confirmed route",
      "Boat / Cruise / Rail: Mekong day trip",
      "Meals included according to plan: Full board",
      "Accommodations, experiences, admission fees, and exclusive arrangements"
    ],
    "exclusions": [
      "International flights to and from destinations",
      "Comprehensive travel insurance",
      "Personal expenses (beverages, laundry, telephone)",
      "Optional experiences not specified in the confirmed itinerary",
      "Tips and gratuities for guides and drivers",
      "Any services not expressly listed as included"
    ],
    "room_notes": "Family Suite / Multi-bedroom Villa"
  },
  "pricing_facts": {
    "conditions": ["Prices based on 10 guests sharing"],
    "options": [
      {
        "id": "opt-standard",
        "label": "Standard Luxury Option",
        "currency": "USD",
        "per_traveler_amount_minor": 50909,
        "group_total_amount_minor": 700000,
        "per_adult_amount_minor": 50909,
        "per_child_amount_minor": None
      }
    ]
  },
  "booking_facts": {
    "title": "Journey for nam vu",
    "description": "Custom luxury journey proposal prepared from enquiry details.",
    "items": []
  },
  "finalization_facts": {
    "required_title": "To Confirm Your Journey",
    "after_confirmation_title": "After Confirmation",
    "required_items": ["30% deposit upon acceptance"],
    "after_confirmation_items": ["Final payment due 45 days prior to arrival"]
  },
  "designer_facts": {
    "seller_subtitle": "Luxury Journey Designer",
    "designer_signature": None,
    "designer_kicker": "Personalized Proposal",
    "designer_quote": "Crafting unforgettable bespoke travel experiences across Indochina.",
    "designer_experience": "Over 10 years of luxury travel design excellence.",
    "designer_title": "Senior Travel Designer",
    "cta_body": "Contact your travel designer to personalize this itinerary."
  },
  "opportunity_id": "req_cdda12b423644000",
  "factMediaSlots": [],
  "content_overrides": {},
  "asset_overrides": {},
  "generation_options": {},
  "retrieval_refs": []
}


def test_destination_default_media_prefix_returns_string():
    dest = DestinationCatalog(
        id="dst_hcm",
        canonical_name="Ho Chi Minh City",
        slug="ho-chi-minh",
        country_slug="vietnam",
        region_slug="south",
        province_slug="ho-chi-minh",
        is_active=True,
        media_prefix=None
    )
    prefix = destination_default_media_prefix(dest)
    assert isinstance(prefix, str)
    assert prefix == "vietnam/south/ho-chi-minh/ho-chi-minh"

    custom_dest = DestinationCatalog(
        id="dst_custom",
        canonical_name="Custom",
        slug="custom",
        country_slug="vietnam",
        region_slug="south",
        province_slug="custom",
        is_active=True,
        media_prefix="destination/custom-folder/"
    )
    custom_prefix = destination_default_media_prefix(custom_dest)
    assert isinstance(custom_prefix, str)
    assert custom_prefix == "destination/custom-folder"


def test_quote_document_destination_ref_preserves_and_serializes():
    doc_dict = {
        "meta": {"quotationId": "quo_test", "lang": "en", "brandId": "selvara", "template": "quote-generator", "revision": 1, "status": "draft", "contentSchemaVersion": 1},
        "content": {"sections": {}},
        "itinerary": {
            "days": [
                {
                    "id": "day-1",
                    "dayNumber": 1,
                    "segmentCity": "Ho Chi Minh City",
                    "destinationRef": {
                        "id": "dst_hcm",
                        "name": "Ho Chi Minh City",
                        "slug": "ho-chi-minh",
                        "coordinates": [10.8231, 106.6297],
                        "mediaPrefix": None,
                        "defaultMediaPrefix": "vietnam/south/ho-chi-minh/ho-chi-minh"
                    }
                }
            ]
        },
        "stays": {
            "hotels": [
                {
                    "id": "hotel-1",
                    "city": "Ho Chi Minh City",
                    "name": "Cicilia Saigon Center",
                    "destinationRef": {
                        "id": "dst_hcm",
                        "name": "Ho Chi Minh City",
                        "slug": "ho-chi-minh",
                        "coordinates": [10.8231, 106.6297],
                        "mediaPrefix": None,
                        "defaultMediaPrefix": "vietnam/south/ho-chi-minh/ho-chi-minh"
                    }
                }
            ]
        }
    }
    validated = QuoteDocumentV1.model_validate(doc_dict)
    serialized = validated.model_dump(mode="json")
    
    # DestinationRef must be preserved
    assert serialized["itinerary"]["days"][0]["destinationRef"] is not None
    assert serialized["itinerary"]["days"][0]["destinationRef"]["slug"] == "ho-chi-minh"
    assert serialized["itinerary"]["days"][0]["destinationRef"]["defaultMediaPrefix"] == "vietnam/south/ho-chi-minh/ho-chi-minh"
    assert serialized["stays"]["hotels"][0]["destinationRef"]["slug"] == "ho-chi-minh"

    # Must be 100% JSON serializable
    json_str = json.dumps(serialized)
    assert "vietnam/south/ho-chi-minh/ho-chi-minh" in json_str


@pytest.mark.anyio
async def test_put_quotation_facts_pipeline_and_concurrency():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    with patch("main._get_db_session_factory", return_value=factory), \
         patch("routers.v2.quotation_facts._get_helpers", return_value=app_main), \
         patch("main.require_owned_quotation", return_value=None):

        async with factory() as session:
            # Seed destination
            dest_repo = DestinationRepository(session)
            await dest_repo.upsert(
                destination_id="dst_ho-chi-minh",
                canonical_name="Ho Chi Minh City",
                slug="ho-chi-minh",
                aliases=["ho chi minh city", "hcm", "saigon"],
                country_slug="vietnam",
                region_slug="south",
                province_slug="ho-chi-minh",
                latitude=10.8231,
                longitude=106.6297,
            )
            # Create designer
            designers = TravelDesignerRepository(session)
            await designers.create_profile(
                profile_id="td_b49deb4d9586",
                name="Nam Designer",
                email="nam@example.com",
                phone="+84123456789",
            )
            # Create quotation
            quotes = QuotationRepository(session)
            documents = QuotationDocumentRepository(session)
            await quotes.create_quotation(
                quotation_id="quo_e4182874ee99",
                opportunity_id="req_cdda12b423644000",
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
            )
            from services.skeleton_builder import SkeletonBuilder
            req = CreateQuoteRequestV1.model_validate(USER_PAYLOAD)
            canonical, resolved = await app_main._resolve_v2_facts(req)
            doc = SkeletonBuilder().build(
                quotation_id="quo_e4182874ee99",
                payload=canonical,
                resolved_facts=resolved,
                template="quote-generator",
            )
            doc["meta"]["revision"] = 1
            await documents.save_current_document(
                quotation_id="quo_e4182874ee99",
                lang="en",
                document_json=doc,
                expected_revision=0,
            )
            await quotes.create_quotation_request(
                quotation_id="quo_e4182874ee99",
                request_json=canonical.model_dump(mode="json"),
            )
            await session.commit()

        principal = Principal(email="test@example.com", role="editor")

        # 1. Test revision conflict (expected 409 Conflict, NOT 500)
        with pytest.raises(HTTPException) as conflict_exc:
            await put_quotation_facts_v2(
                quotation_id="quo_e4182874ee99",
                payload=req,
                baseRevision=16,
                principal=principal,
            )
        assert conflict_exc.value.status_code == 409
        assert conflict_exc.value.detail["message"] == "Facts revision conflict."
        assert conflict_exc.value.detail["currentRevision"] == 1

        # 2. Test successful update with matching baseRevision (expected 200 OK and revision increment)
        res = await put_quotation_facts_v2(
            quotation_id="quo_e4182874ee99",
            payload=req,
            baseRevision=1,
            principal=principal,
        )
        assert res["currentRevision"] == 2
        assert res["facts"]["trip_facts"]["destinations"] == ["Ho Chi Minh City"]
        # Verify JSON serialization of saved document
        async with factory() as session:
            saved_doc = await QuotationDocumentRepository(session).get_current_document("quo_e4182874ee99", "en")
            assert saved_doc is not None
            assert saved_doc.revision == 2
            # Must serialize with standard json.dumps cleanly
            raw_json = json.dumps(saved_doc.document_json)
            assert "Ho Chi Minh City" in raw_json

    await engine.dispose()

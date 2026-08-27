import unittest
from unittest.mock import AsyncMock, MagicMock

from db.models.quote_request import QuoteRequest
from schemas.v2.quote_request import QuoteRequestCreateSchema
from services.quote_request_service import (
    QuoteRequestService,
    convert_request_to_quotation_facts,
    derive_children_details,
    parse_advisor_dates_to_iso,
)


class TestQuoteRequestService(unittest.IsolatedAsyncioTestCase):
    def test_parse_advisor_dates_to_iso(self):
        start, end = parse_advisor_dates_to_iso("09–20 Nov 2026")
        self.assertEqual(start, "2026-11-09")
        self.assertEqual(end, "2026-11-20")

        start, end = parse_advisor_dates_to_iso("2026-11-09 to 2026-11-20")
        self.assertEqual(start, "2026-11-09")
        self.assertEqual(end, "2026-11-20")

        start, end = parse_advisor_dates_to_iso("flexible timing")
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_derive_children_details(self):
        self.assertEqual(derive_children_details(0, []), "")
        self.assertEqual(derive_children_details(2, [6, 11]), "2 children (ages 6, 11)")
        self.assertEqual(derive_children_details(1, [8]), "1 child (age 8)")

    def test_convert_request_to_quotation_facts(self):
        req = QuoteRequest(
            id="req_test_123",
            role="traveller",
            customer_name="Eleanor Vance",
            email="eleanor@example.com",
            destinations=["Vietnam", "Cambodia"],
            start_date="2026-11-09",
            end_date="2026-11-20",
            adults=2,
            children=2,
            kid_ages=[6, 11],
            travel_style="Living Heritage",
            special_requirements="Private guides and dietary requirements",
            payload_json={
                "itinerary_days": [
                    {"day_number": 1, "destination": "Hanoi", "summary": "Arrival & food tour", "overnight": "Hanoi"},
                    {"day_number": 2, "destination": "Ninh Binh", "summary": "Trang An boat trip", "overnight": "Ninh Binh"},
                ]
            },
        )
        facts = convert_request_to_quotation_facts(req)

        self.assertEqual(facts["customer_facts"]["customer_name"], "Eleanor Vance")
        self.assertEqual(facts["customer_facts"]["adults"], 2)
        self.assertEqual(facts["customer_facts"]["children"], 2)
        self.assertEqual(facts["trip_facts"]["destinations"], ["Vietnam", "Cambodia"])
        self.assertEqual(len(facts["trip_facts"]["itinerary"]), 2)
        self.assertEqual(facts["trip_facts"]["itinerary"][0]["summary"], "Arrival & food tour")

    def test_convert_full_intake_request_to_quotation_facts(self):
        req = QuoteRequest(
            id="req_intake_999",
            role="advisor",
            customer_name="Mr. Alexander Wright",
            email="alex@luxurytravel.com",
            phone="+44 7700 900077",
            company_name="Wright Luxury Escapes",
            market="United Kingdom",
            destinations=["Vietnam", "Laos"],
            start_date="2026-11-10",
            end_date="2026-11-24",
            adults=2,
            children=1,
            kid_ages=[9],
            travel_style="Living Heritage",
            special_requirements="VIP client anniversary trip",
            created_by_profile_id="designer_007",
            payload_json={
                "brand_id": "selvara",
                "travel_designer_id": "designer_007",
                "budget": 12000.0,
                "budget_basis": "Total trip",
                "currency": "GBP",
                "room_configuration": "1 King Suite + 1 Extra Bed",
                "dietary": "Gluten-free for Mrs. Wright",
                "halal": "No pork",
                "mobility": "Ground floor rooms preferred",
                "visa_fasttrack": "Yes",
                "private_vehicle": "Yes",
                "vehicle_preference": "VIP Mercedes Van",
                "guide_scope": "Full-trip guide",
                "guide_language": "English",
                "domestic_flights": "Yes",
                "meal_plan": "Half board",
            },
        )
        facts = convert_request_to_quotation_facts(req)

        self.assertEqual(facts["brand_id"], "selvara")
        self.assertEqual(facts["presentation_options"]["travel_designer_id"], "designer_007")
        self.assertEqual(facts["customer_facts"]["customer_name"], "Mr. Alexander Wright")
        self.assertEqual(facts["service_facts"]["room_notes"], "1 King Suite + 1 Extra Bed")

        # Verify special requirements consolidated
        reqs_str = " ".join(facts["trip_facts"]["special_requirements"])
        self.assertIn("VIP client anniversary trip", reqs_str)
        self.assertIn("Gluten-free", reqs_str)
        self.assertIn("No pork", reqs_str)
        self.assertIn("Ground floor", reqs_str)

        # Verify pricing options derived from budget & GBP
        self.assertEqual(facts["pricing_facts"]["options"][0]["currency"], "GBP")
        self.assertEqual(facts["pricing_facts"]["options"][0]["group_total_amount_minor"], 1200000)
        self.assertEqual(facts["pricing_facts"]["options"][0]["per_traveler_amount_minor"], 600000)

        # Verify service inclusions
        inclusions_str = " ".join(facts["service_facts"]["inclusions"])
        self.assertIn("fast-track", inclusions_str)
        self.assertIn("VIP Mercedes Van", inclusions_str)
        self.assertIn("Full-trip private English-speaking", inclusions_str)
        self.assertIn("Domestic flights", inclusions_str)

    async def test_honeypot_rejection(self):
        mock_session = AsyncMock()
        service = QuoteRequestService(mock_session)
        payload = QuoteRequestCreateSchema(
            role="traveller",
            customer_name="Bot User",
            email="bot@spam.com",
            website="http://spam.com",
        )
        with self.assertRaises(ValueError):
            await service.create_quote_request(payload)

    def test_convert_b2b_advisor_with_client_name(self):
        req = QuoteRequest(
            id="req_b2b_777",
            role="advisor",
            customer_name="Sarah Jenkins",
            email="sarah@virtuoso.co.uk",
            company_name="Virtuoso Luxury Travel",
            market="United Kingdom",
            destinations=["Vietnam"],
            adults=2,
            children=0,
            partner_id="ptn_virtuoso_01",
            payload_json={
                "client_name": "The Vance Family",
                "partner_id": "ptn_virtuoso_01",
                "routing_constraints": "Arrival on VN50 at 06:30",
                "priority_1": "Bespoke culinary encounters",
                "must_have": "Top-floor suites with balcony",
                "avoid": "Large tour groups",
                "show_commission": "Yes — separate line",
                "commission": 15.0,
                "price_display": "Per person sharing",
            },
        )
        facts = convert_request_to_quotation_facts(req)

        # Customer name should be the End-Client name
        self.assertEqual(facts["customer_facts"]["customer_name"], "The Vance Family")
        self.assertEqual(facts["customer_facts"]["advisor_name"], "Sarah Jenkins")
        self.assertEqual(facts["customer_facts"]["advisor_agency"], "Virtuoso Luxury Travel")
        self.assertEqual(facts["presentation_options"]["partner_id"], "ptn_virtuoso_01")

        # Booking title & description
        self.assertEqual(facts["booking_facts"]["title"], "Journey for The Vance Family")
        self.assertIn("prepared for Sarah Jenkins (Virtuoso Luxury Travel)", facts["booking_facts"]["description"])

        # Trip facts & constraints
        self.assertEqual(facts["trip_facts"]["routing_constraints"], "Arrival on VN50 at 06:30")
        self.assertIn("Bespoke culinary encounters", facts["trip_facts"]["priorities"])
        self.assertEqual(facts["trip_facts"]["must_have"], "Top-floor suites with balcony")
        self.assertEqual(facts["trip_facts"]["avoid"], "Large tour groups")

        # Pricing facts
        self.assertEqual(len(facts["pricing_facts"]["options"]), 1)
        self.assertIn("sharing", facts["pricing_facts"]["conditions"][0])

    def test_consolidate_stays_from_day_accommodations(self):
        from services.quote_request_service import consolidate_stays_from_day_accommodations

        itinerary_with_stays = [
            {"day_number": 1, "destination": "Hanoi", "accommodation_id": "acc_capella", "accommodation_name": "Capella Hanoi", "room_type": "Premier Suite"},
            {"day_number": 2, "destination": "Hanoi", "accommodation_id": "acc_capella", "accommodation_name": "Capella Hanoi", "room_type": "Premier Suite"},
            {"day_number": 3, "destination": "Ninh Binh", "accommodation_id": "acc_emeralda", "accommodation_name": "Emeralda Resort", "room_type": "Superior Room"},
            {"day_number": 4, "destination": "Halong Bay", "accommodation_id": "acc_paradise", "accommodation_name": "Paradise Peak Cruise", "room_type": "Ocean Suite"},
            {"day_number": 5, "destination": "Hanoi", "accommodation_id": None, "accommodation_name": None, "room_type": None},
        ]
        stays = consolidate_stays_from_day_accommodations(itinerary_with_stays, "2026-10-12")

        self.assertEqual(len(stays), 3)

        # Stay 1: Capella Hanoi (Day 1 + Day 2)
        self.assertEqual(stays[0]["accommodation_id"], "acc_capella")
        self.assertEqual(stays[0]["name"], "Capella Hanoi")
        self.assertEqual(stays[0]["check_in"], "2026-10-12")
        self.assertEqual(stays[0]["check_out"], "2026-10-14")

        # Stay 2: Emeralda Resort (Day 3)
        self.assertEqual(stays[1]["accommodation_id"], "acc_emeralda")
        self.assertEqual(stays[1]["check_in"], "2026-10-14")
        self.assertEqual(stays[1]["check_out"], "2026-10-15")

        # Stay 3: Paradise Peak (Day 4)
        self.assertEqual(stays[2]["accommodation_id"], "acc_paradise")
        self.assertEqual(stays[2]["check_in"], "2026-10-15")
        self.assertEqual(stays[2]["check_out"], "2026-10-16")

    def test_convert_request_with_minimal_overrides(self):
        from schemas.v2.quote_request import (
            MinimalCommercialPricingOverrideSchema,
            MinimalItineraryDayWithStayOverrideSchema,
            QuotationMinimalOverridesSchema,
        )

        req = QuoteRequest(
            id="req_base_001",
            role="traveller",
            customer_name="Original Name",
            email="orig@example.com",
            adults=2,
            children=0,
            destinations=["Vietnam"],
            start_date="2026-10-01",
            end_date="2026-10-05",
            payload_json={"brand_id": "selvara"},
        )

        overrides = QuotationMinimalOverridesSchema(
            brand_id="vietnam_safar",
            customer_name="Mr. David Jenkins",
            adults=2,
            children=1,
            kid_ages=[8],
            start_date="2026-10-12",
            end_date="2026-10-16",
            itinerary_with_stays=[
                MinimalItineraryDayWithStayOverrideSchema(day_number=1, destination="Hanoi", accommodation_id="acc_capella", accommodation_name="Capella Hanoi", room_type="Suite", summary="Arrival dinner"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=2, destination="Hanoi", accommodation_id="acc_capella", accommodation_name="Capella Hanoi", room_type="Suite", summary="Old quarter tour"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=3, destination="Halong Bay", accommodation_id="acc_cruise", accommodation_name="Heritage Cruise", room_type="Cabin", summary="Cruise excursion"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=4, destination="Hanoi", accommodation_id=None, summary="Departure"),
            ],
            pricing=MinimalCommercialPricingOverrideSchema(
                label="Bespoke Safar Option",
                currency="USD",
                per_adult_amount_minor=400000,
                per_child_amount_minor=250000,
                group_total_amount_minor=1050000,
            ),
        )

        facts = convert_request_to_quotation_facts(req, overrides)

        # Brand & Customer Overrides
        self.assertEqual(facts["brand_id"], "vietnam_safar")
        self.assertEqual(facts["customer_facts"]["customer_name"], "Mr. David Jenkins")
        self.assertEqual(facts["customer_facts"]["adults"], 2)
        self.assertEqual(facts["customer_facts"]["children"], 1)
        self.assertEqual(facts["customer_facts"]["kid_ages"], [8])
        self.assertIn("1 child (age 8)", facts["customer_facts"]["party_label"])

        # Trip Dates & Duration
        self.assertEqual(facts["trip_facts"]["start_date"], "2026-10-12")
        self.assertEqual(facts["trip_facts"]["end_date"], "2026-10-16")
        self.assertEqual(len(facts["trip_facts"]["itinerary"]), 4)
        self.assertEqual(facts["trip_facts"]["itinerary"][0]["destination"], "Hanoi")
        self.assertEqual(facts["trip_facts"]["itinerary"][0]["display_date"], "2026-10-12")

        # Stays Consolidated
        hotels = facts["service_facts"]["hotels"]
        self.assertEqual(len(hotels), 2)
        self.assertEqual(hotels[0]["name"], "Capella Hanoi")
        self.assertEqual(hotels[0]["check_in"], "2026-10-12")
        self.assertEqual(hotels[0]["check_out"], "2026-10-14")

        # 3-Parameter Commercial Pricing
        pricing_opt = facts["pricing_facts"]["options"][0]
        self.assertEqual(pricing_opt["label"], "Bespoke Safar Option")
        self.assertEqual(pricing_opt["currency"], "USD")
        self.assertEqual(pricing_opt["per_traveler_amount_minor"], 400000)
        self.assertEqual(pricing_opt["group_total_amount_minor"], 1050000)

    def test_generate_quotation_with_added_days_overrides(self):
        from schemas.v2.quote_request import (
            MinimalItineraryDayWithStayOverrideSchema,
            QuotationMinimalOverridesSchema,
        )

        req = QuoteRequest(
            id="req_expand_001",
            role="traveller",
            customer_name="Alice Johnson",
            email="alice@example.com",
            destinations=["Hanoi"],
            start_date="2026-11-01",
            end_date="2026-11-03",
            adults=2,
            children=0,
            payload_json={
                "itinerary_days": [
                    {"day_number": 1, "destination": "Hanoi", "summary": "Arrival"},
                    {"day_number": 2, "destination": "Hanoi", "summary": "City tour"},
                    {"day_number": 3, "destination": "Hanoi", "summary": "Food tour"},
                ]
            },
        )

        # User added Day 4 (Hue) and Day 5 (Da Nang) on New Quotation screen
        overrides = QuotationMinimalOverridesSchema(
            start_date="2026-11-01",
            end_date="2026-11-05",
            itinerary_with_stays=[
                MinimalItineraryDayWithStayOverrideSchema(day_number=1, destination="Hanoi", accommodation_id="acc_metropole", accommodation_name="Sofitel Metropole", room_type="Deluxe"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=2, destination="Hanoi", accommodation_id="acc_metropole", accommodation_name="Sofitel Metropole", room_type="Deluxe"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=3, destination="Hanoi", accommodation_id="acc_metropole", accommodation_name="Sofitel Metropole", room_type="Deluxe"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=4, destination="Hue", accommodation_id="acc_azerai", accommodation_name="Azerai La Residence", room_type="River View"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=5, destination="Da Nang", accommodation_id="acc_intercon", accommodation_name="InterContinental Danang", room_type="Ocean View"),
            ],
        )

        facts = convert_request_to_quotation_facts(req, overrides)

        self.assertEqual(facts["trip_facts"]["start_date"], "2026-11-01")
        self.assertEqual(facts["trip_facts"]["end_date"], "2026-11-05")
        self.assertEqual(facts["trip_facts"]["duration_days"], 5)
        self.assertEqual(facts["trip_facts"]["duration_nights"], 4)
        self.assertEqual(len(facts["trip_facts"]["itinerary"]), 5)
        self.assertEqual(facts["trip_facts"]["itinerary"][3]["destination"], "Hue")
        self.assertEqual(facts["trip_facts"]["itinerary"][4]["destination"], "Da Nang")
        self.assertIn("Hue", facts["trip_facts"]["destinations"])
        self.assertIn("Da Nang", facts["trip_facts"]["destinations"])

        # Check hotel stays consolidation
        hotels = facts["service_facts"]["hotels"]
        self.assertEqual(len(hotels), 3)
        self.assertEqual(hotels[0]["name"], "Sofitel Metropole")
        self.assertEqual(hotels[0]["check_in"], "2026-11-01")
        self.assertEqual(hotels[0]["check_out"], "2026-11-04")
        self.assertEqual(hotels[1]["name"], "Azerai La Residence")
        self.assertEqual(hotels[1]["check_in"], "2026-11-04")
        self.assertEqual(hotels[1]["check_out"], "2026-11-05")
        self.assertEqual(hotels[2]["name"], "InterContinental Danang")
        self.assertEqual(hotels[2]["check_in"], "2026-11-05")
        self.assertEqual(hotels[2]["check_out"], "2026-11-06")

    def test_generate_quotation_with_removed_days_overrides(self):
        from schemas.v2.quote_request import (
            MinimalItineraryDayWithStayOverrideSchema,
            QuotationMinimalOverridesSchema,
        )

        req = QuoteRequest(
            id="req_shrink_001",
            role="traveller",
            customer_name="Bob Miller",
            email="bob@example.com",
            destinations=["Hanoi", "Halong", "Hue", "Hoi An"],
            start_date="2026-11-01",
            end_date="2026-11-04",
            adults=2,
            children=0,
            payload_json={
                "itinerary_days": [
                    {"day_number": 1, "destination": "Hanoi"},
                    {"day_number": 2, "destination": "Halong"},
                    {"day_number": 3, "destination": "Hue"},
                    {"day_number": 4, "destination": "Hoi An"},
                ]
            },
        )

        # User removed Day 3 and Day 4 on New Quotation screen, keeping only 2 days in Hanoi
        overrides = QuotationMinimalOverridesSchema(
            start_date="2026-11-01",
            end_date="2026-11-02",
            itinerary_with_stays=[
                MinimalItineraryDayWithStayOverrideSchema(day_number=1, destination="Hanoi", accommodation_id="acc_metropole", accommodation_name="Sofitel Metropole", room_type="Deluxe"),
                MinimalItineraryDayWithStayOverrideSchema(day_number=2, destination="Hanoi", accommodation_id="acc_metropole", accommodation_name="Sofitel Metropole", room_type="Deluxe"),
            ],
        )

        facts = convert_request_to_quotation_facts(req, overrides)

        self.assertEqual(facts["trip_facts"]["start_date"], "2026-11-01")
        self.assertEqual(facts["trip_facts"]["end_date"], "2026-11-02")
        self.assertEqual(facts["trip_facts"]["duration_days"], 2)
        self.assertEqual(facts["trip_facts"]["duration_nights"], 1)
        self.assertEqual(len(facts["trip_facts"]["itinerary"]), 2)
        self.assertEqual(facts["trip_facts"]["destinations"], ["Hanoi"])

        # Stays consolidated to 1 hotel segment
        hotels = facts["service_facts"]["hotels"]
        self.assertEqual(len(hotels), 1)
        self.assertEqual(hotels[0]["name"], "Sofitel Metropole")
        self.assertEqual(hotels[0]["check_in"], "2026-11-01")
        self.assertEqual(hotels[0]["check_out"], "2026-11-03")

    async def test_generate_quotation_preserves_creator_when_assigned_to_different_designer(self):
        from unittest.mock import patch
        mock_session = AsyncMock()
        service = QuoteRequestService(mock_session)

        req = QuoteRequest(
            id="req_preservation_001",
            role="traveller",
            customer_name="Alice Smith",
            email="alice@example.com",
            destinations=["Hanoi"],
            start_date="2026-11-01",
            end_date="2026-11-03",
            adults=2,
            children=0,
            payload_json={"brand_id": "selvara", "travel_designer_id": "td_assigned"},
        )
        service.repo.get_by_id = AsyncMock(return_value=req)
        service.repo.update_status = AsyncMock()

        from quote_document import CreateQuoteRequestV1
        mock_quotation = MagicMock(id="quo_test_123")
        mock_saved_doc = MagicMock(revision=1)
        mock_canonical = CreateQuoteRequestV1.model_validate({
            "brand_id": "selvara",
            "presentation_options": {"theme_id": "brochure", "layout_version": 1, "travel_designer_id": "td_assigned"},
            "trip_facts": {"destinations": ["Hanoi"], "itinerary": []},
            "customer_facts": {"customer_name": "Alice Smith"},
            "pricing_facts": {"conditions": [], "options": []},
            "service_facts": {"hotels": [], "inclusions": [], "exclusions": []},
            "booking_facts": {"title": "Terms", "description": "Standard terms apply", "items": []},
            "designer_facts": {},
        })
        mock_resolved = {
            "duration": {"label": "3 days / 2 nights"},
            "routeLabel": "Hanoi",
            "travelDateLabel": "01 - 03 Nov 2026",
            "itinerary": [],
        }

        with patch("main._resolve_v2_facts", new_callable=AsyncMock, return_value=(mock_canonical, mock_resolved)), \
             patch("main._apply_missing_media_defaults", new_callable=AsyncMock), \
             patch("main._serialize_travel_designer", return_value={"id": "td_assigned", "name": "Assigned Designer"}), \
             patch("repositories.quotation_repository.QuotationRepository.create_quotation", new_callable=AsyncMock) as mock_create_quote, \
             patch("repositories.quotation_repository.QuotationRepository.create_quotation_request", new_callable=AsyncMock), \
             patch("repositories.quotation_repository.QuotationDocumentRepository.save_current_document", new_callable=AsyncMock, return_value=mock_saved_doc), \
             patch("repositories.quotation_repository.QuotationDocumentRepository.append_document_revision", new_callable=AsyncMock), \
             patch("services.outbox_service.OutboxService.emit_event", new_callable=AsyncMock), \
             patch("repositories.travel_designer_repository.TravelDesignerRepository.get_profile", new_callable=AsyncMock) as mock_get_profile:

            mock_profile = MagicMock(id="td_assigned", email="assigned@example.com", name="Assigned Designer")
            mock_get_profile.return_value = mock_profile
            mock_create_quote.return_value = mock_quotation

            # User who clicks generate is td_creator, while the quote is assigned to td_assigned
            result = await service.generate_quotation_from_request(
                request_id="req_preservation_001",
                created_by_profile_id="td_creator",
            )

            self.assertEqual(result["quotation_id"], "quo_test_123")
            mock_create_quote.assert_called_once()
            call_kwargs = mock_create_quote.call_args.kwargs
            # Verify creator profile ID was preserved and not overwritten by resolved designer
            self.assertEqual(call_kwargs["created_by_profile_id"], "td_creator")
            self.assertEqual(call_kwargs["designer_profile_id"], "td_assigned")

    def test_convert_request_to_quotation_facts_multiple_pricing_options(self):
        from schemas.v2.quote_request import (
            QuotationMinimalOverridesSchema,
            MinimalCommercialPricingOverrideSchema,
        )

        req = MagicMock(spec=QuoteRequest)
        req.adults = 2
        req.children = 1
        req.kid_ages = [6]
        req.start_date = "2026-11-01"
        req.end_date = "2026-11-05"
        req.customer_name = "Mr. Wayne"
        req.role = "traveller"
        req.destinations = ["Hanoi", "Halong"]
        req.special_requirements = None
        req.children_details = None
        req.created_by_profile_id = None
        req.partner_id = None
        req.payload_json = {"currency": "USD"}

        overrides = QuotationMinimalOverridesSchema(
            pricing_options=[
                MinimalCommercialPricingOverrideSchema(
                    label="Standard Option",
                    currency="USD",
                    per_adult_amount_minor=300000,
                    per_child_amount_minor=150000,
                    group_total_amount_minor=750000,
                ),
                MinimalCommercialPricingOverrideSchema(
                    label="Premium Option",
                    currency="USD",
                    per_adult_amount_minor=450000,
                    per_child_amount_minor=225000,
                    group_total_amount_minor=1125000,
                ),
            ]
        )

        facts = convert_request_to_quotation_facts(req, overrides)
        pricing_facts = facts.get("pricing_facts", {})
        options = pricing_facts.get("options", [])

        self.assertEqual(len(options), 2)
        self.assertEqual(options[0]["label"], "Standard Option")
        self.assertEqual(options[0]["per_traveler_amount_minor"], 300000)
        self.assertEqual(options[0]["group_total_amount_minor"], 750000)

        self.assertEqual(options[1]["label"], "Premium Option")
        self.assertEqual(options[1]["per_traveler_amount_minor"], 450000)
        self.assertEqual(options[1]["group_total_amount_minor"], 1125000)

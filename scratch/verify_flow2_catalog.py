import asyncio
import os
import tempfile
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

import db.session as db_session
import main
from db.base import Base
from db.models.accommodation import AccommodationProfile
from db.models.destination import DestinationCatalog
from db.models.supplier import Supplier
from db.models.product import Product
from services.supplier_service import normalize_supplier_name
from core.rules.catalog_vocab import (
    CATEGORY,
    UNIT,
    TIME_BASIS,
    DEFAULT_CHARGE_UNIT_BY_CATEGORY,
    SUBCATEGORY_BY_CATEGORY,
    DESTINATION_TYPE,
    DESTINATION_TYPE_RANK,
)

async def run_verification():
    results = {
        "summary": {},
        "r2_invariant": {},
        "vocab_ssot": {},
        "fixtures_created": [],
        "invariants_tested": [],
        "destination_tested": [],
    }

    # 1. Setup SQLite test database
    temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
    temp_db.close()
    engine = create_async_engine(f"sqlite+aiosqlite:///{temp_db.name}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_patch1 = patch.object(db_session, "get_session_factory", return_value=session_factory)
    session_patch2 = patch.object(main, "_get_db_session_factory", return_value=session_factory)
    session_patch1.start()
    session_patch2.start()
    auth_patch = patch.dict(
        os.environ, {"DMC_GATEWAY_ENABLED": "false", "QUOTE_AUTH_REQUIRED": "false", "ENVIRONMENT": "local"}
    )
    auth_patch.start()

    client = TestClient(main.app)

    try:
        # Seed Base Hub & Suppliers & Accommodation
        async with session_factory() as session:
            await main._seed_destination_catalog(session)

            # Suppliers (Flow 1 Creditor registry)
            sup_metropole = Supplier(
                id="sup_metropole_dmc",
                name="Sofitel Legend Metropole Hanoi",
                name_normalized=normalize_supplier_name("Sofitel Legend Metropole Hanoi"),
                legal_name="Metropole Hotel Joint Venture Company",
                supplier_type="hotel",
                country="Vietnam",
                city="Hanoi",
                default_currency="USD",
            )
            sup_transport = Supplier(
                id="sup_capella_transport",
                name="Capella Luxury Transport Services",
                name_normalized=normalize_supplier_name("Capella Luxury Transport Services"),
                legal_name="Capella Transport & Travel Logistics JSC",
                supplier_type="dmc",
                country="Vietnam",
                city="Hanoi",
                default_currency="USD",
            )
            sup_street_bites = Supplier(
                id="sup_hanoi_street_bites",
                name="Hanoi Culinary Explorers & Street Bites",
                name_normalized=normalize_supplier_name("Hanoi Culinary Explorers & Street Bites"),
                legal_name="Hanoi Food Tours Co., Ltd",
                supplier_type="activity_vendor",
                country="Vietnam",
                city="Hanoi",
                default_currency="USD",
            )
            sup_vn_airlines = Supplier(
                id="sup_vietnam_airlines",
                name="Vietnam Airlines JSC",
                name_normalized=normalize_supplier_name("Vietnam Airlines JSC"),
                legal_name="Vietnam Airlines Joint Stock Company",
                supplier_type="airline",
                country="Vietnam",
                city="Hanoi",
                default_currency="VND",
            )
            session.add_all([sup_metropole, sup_transport, sup_street_bites, sup_vn_airlines])

            # Accommodation Profile (Content layer)
            acc_metropole = AccommodationProfile(
                id="acc_metropole_hanoi",
                destination_id="dst_ha-noi",
                storage_slug="sofitel-legend-metropole",
                asset_prefix="hanoi/sofitel-legend-metropole",
                name="Sofitel Legend Metropole Hanoi",
                room_type="Grand Luxury Room",
                intro="An iconic French colonial hotel in the heart of Hanoi.",
            )
            session.add(acc_metropole)

            await session.commit()

        # -------------------------------------------------------------
        # STEP 1: Assert R2 Invariant (Product != Rate)
        # -------------------------------------------------------------
        product_table = Product.__table__
        column_names = [col.name for col in product_table.columns]
        forbidden_terms = ["amount", "price", "currency", "minor", "rate", "cost", "fee"]
        leaked_columns = [col for col in column_names if any(t in col.lower() for t in forbidden_terms)]

        results["r2_invariant"] = {
            "total_columns": len(column_names),
            "columns": column_names,
            "forbidden_terms_checked": forbidden_terms,
            "leaked_columns": leaked_columns,
            "status": "PASSED - ZERO pricing columns on products table",
        }
        assert not leaked_columns, f"R2 Invariant Violated! Leaked pricing columns found: {leaked_columns}"

        # -------------------------------------------------------------
        # STEP 2: Assert 10-Category SSOT & Vocab Structure
        # -------------------------------------------------------------
        results["vocab_ssot"] = {
            "categories_count": len(CATEGORY),
            "categories": sorted(list(CATEGORY)),
            "charge_units_count": len(UNIT),
            "charge_units": sorted(list(UNIT)),
            "time_bases": sorted(list(TIME_BASIS)),
            "default_mappings": {k: f"{v[0]} × {v[1]}" for k, v in DEFAULT_CHARGE_UNIT_BY_CATEGORY.items()},
        }
        assert len(CATEGORY) == 10, f"Expected 10 categories, got {len(CATEGORY)}"

        # -------------------------------------------------------------
        # STEP 3: Multi-Category Product Fixtures Creation via API
        # -------------------------------------------------------------

        # 3.1 Accommodation Product
        acc_payload = {
            "supplier_id": "sup_metropole_dmc",
            "property_id": "acc_metropole_hanoi",
            "destination_id": "dst_ha-noi",
            "category": "accommodation",
            "subcategory": "hotel",
            "supplier_product_name": "Grand Luxury Room (Metropole Historic Wing)",
            "title": "Metropole Grand Luxury Room",
            "unit": "room",
            "time_basis": "night",
            "default_min_pax": 1,
            "default_max_pax": 2,
            "category_attributes": {
                "room_type": "dbl",
                "meal_plan": "bb",
                "view": "historic_courtyard",
                "bed_config": "1 king bed",
            },
        }
        res_acc = client.post("/api/v2/products", json=acc_payload)
        assert res_acc.status_code == 201, f"Failed creating accommodation product: {res_acc.text}"
        prod_acc = res_acc.json()
        results["fixtures_created"].append({
            "fixture": "Accommodation Product",
            "id": prod_acc["id"],
            "title": prod_acc["title"],
            "category": prod_acc["category"],
            "subcategory": prod_acc["subcategory"],
            "unit_x_time_basis": f"{prod_acc['unit']} × {prod_acc['time_basis']}",
            "supplier_id": prod_acc["supplier_id"],
            "property_id": prod_acc["property_id"],
            "destination_id": prod_acc["destination_id"],
            "origin_destination_id": prod_acc["origin_destination_id"],
            "supplier_product_name": prod_acc["supplier_product_name"],
        })

        # 3.2 Transportation Route Product (Point-to-Point: Hanoi -> Ha Long)
        trans_payload = {
            "supplier_id": "sup_capella_transport",
            "destination_id": "dst_quang-ninh",
            "origin_destination_id": "dst_ha-noi",
            "category": "transportation",
            "subcategory": "van_16_seat",
            "supplier_product_name": "Ford Transit 16-Seat Private Chauffeur Hanoi -> Halong",
            "title": "Private Van Transfer Hanoi - Halong",
            "unit": "vehicle",
            "time_basis": "trip",
            "default_min_pax": 1,
            "default_max_pax": 10,
            "category_attributes": {
                "vehicle_type": "Ford Transit Luxury 2025",
                "seat_capacity": 16,
                "has_driver": True,
                "has_wifi": True,
            },
        }
        res_trans = client.post("/api/v2/products", json=trans_payload)
        assert res_trans.status_code == 201, f"Failed creating transport product: {res_trans.text}"
        prod_trans = res_trans.json()
        results["fixtures_created"].append({
            "fixture": "Transportation Route Product",
            "id": prod_trans["id"],
            "title": prod_trans["title"],
            "category": prod_trans["category"],
            "subcategory": prod_trans["subcategory"],
            "unit_x_time_basis": f"{prod_trans['unit']} × {prod_trans['time_basis']}",
            "supplier_id": prod_trans["supplier_id"],
            "property_id": prod_trans["property_id"],
            "destination_id": prod_trans["destination_id"],
            "origin_destination_id": prod_trans["origin_destination_id"],
            "supplier_product_name": prod_trans["supplier_product_name"],
        })

        # 3.3 Activity / Experience Product
        exp_payload = {
            "supplier_id": "sup_hanoi_street_bites",
            "destination_id": "dst_ha-noi",
            "category": "experience",
            "subcategory": "food_tour",
            "supplier_product_name": "Hanoi Old Quarter Street Food Walking & Egg Coffee Experience",
            "title": "Hanoi Street Food Walking Tour",
            "unit": "person",
            "time_basis": "trip",
            "default_min_pax": 2,
            "default_max_pax": 8,
            "category_attributes": {
                "duration_hours": 4,
                "group_max": 8,
                "physical_level": "easy_walk",
                "includes_egg_coffee": True,
            },
        }
        res_exp = client.post("/api/v2/products", json=exp_payload)
        assert res_exp.status_code == 201, f"Failed creating experience product: {res_exp.text}"
        prod_exp = res_exp.json()
        results["fixtures_created"].append({
            "fixture": "Activity/Experience Product",
            "id": prod_exp["id"],
            "title": prod_exp["title"],
            "category": prod_exp["category"],
            "subcategory": prod_exp["subcategory"],
            "unit_x_time_basis": f"{prod_exp['unit']} × {prod_exp['time_basis']}",
            "supplier_id": prod_exp["supplier_id"],
            "property_id": prod_exp["property_id"],
            "destination_id": prod_exp["destination_id"],
            "origin_destination_id": prod_exp["origin_destination_id"],
            "supplier_product_name": prod_exp["supplier_product_name"],
        })

        # 3.4 Guide Product
        guide_payload = {
            "destination_id": "dst_ha-noi",
            "category": "guide",
            "subcategory": "local_guide",
            "title": "Hanoi Historic & French Quarter Full-Day English Guide",
            "supplier_product_name": "English Speaking Local Tour Guide Full Day",
            "unit": "group",
            "time_basis": "day",
            "category_attributes": {"language": "English", "specialty": "colonial_architecture_history"},
        }
        res_guide = client.post("/api/v2/products", json=guide_payload)
        assert res_guide.status_code == 201
        prod_guide = res_guide.json()
        results["fixtures_created"].append({
            "fixture": "Tour Guide Product",
            "id": prod_guide["id"],
            "title": prod_guide["title"],
            "category": prod_guide["category"],
            "subcategory": prod_guide["subcategory"],
            "unit_x_time_basis": f"{prod_guide['unit']} × {prod_guide['time_basis']}",
            "supplier_id": prod_guide["supplier_id"],
            "property_id": prod_guide["property_id"],
            "destination_id": prod_guide["destination_id"],
            "origin_destination_id": prod_guide["origin_destination_id"],
            "supplier_product_name": prod_guide["supplier_product_name"],
        })

        # 3.5 Flight Product (Point-to-Point: Hanoi -> Da Nang)
        flight_payload = {
            "supplier_id": "sup_vietnam_airlines",
            "origin_destination_id": "dst_ha-noi",
            "destination_id": "dst_da-nang",
            "category": "flights",
            "subcategory": "domestic_flight",
            "title": "Vietnam Airlines Domestic Flight HAN -> DAD",
            "supplier_product_name": "VN Airlines One-way Economy Class HAN-DAD",
            "unit": "flight_seat",
            "time_basis": "trip",
            "category_attributes": {"cabin_class": "economy", "airline": "Vietnam Airlines"},
        }
        res_flight = client.post("/api/v2/products", json=flight_payload)
        assert res_flight.status_code == 201
        prod_flight = res_flight.json()
        results["fixtures_created"].append({
            "fixture": "Flight Route Product",
            "id": prod_flight["id"],
            "title": prod_flight["title"],
            "category": prod_flight["category"],
            "subcategory": prod_flight["subcategory"],
            "unit_x_time_basis": f"{prod_flight['unit']} × {prod_flight['time_basis']}",
            "supplier_id": prod_flight["supplier_id"],
            "property_id": prod_flight["property_id"],
            "destination_id": prod_flight["destination_id"],
            "origin_destination_id": prod_flight["origin_destination_id"],
            "supplier_product_name": prod_flight["supplier_product_name"],
        })

        # 3.6 Ticket Product
        ticket_payload = {
            "destination_id": "dst_ha-noi",
            "category": "ticket",
            "subcategory": "performance",
            "title": "Thang Long Water Puppet Theater VIP Ticket",
            "supplier_product_name": "Thang Long Water Puppet VIP Front Row Ticket",
            "unit": "person",
            "time_basis": "trip",
            "category_attributes": {"admission_type": "vip_front_row", "skip_line": True},
        }
        res_ticket = client.post("/api/v2/products", json=ticket_payload)
        assert res_ticket.status_code == 201
        prod_ticket = res_ticket.json()
        results["fixtures_created"].append({
            "fixture": "Ticket / Admission Product",
            "id": prod_ticket["id"],
            "title": prod_ticket["title"],
            "category": prod_ticket["category"],
            "subcategory": prod_ticket["subcategory"],
            "unit_x_time_basis": f"{prod_ticket['unit']} × {prod_ticket['time_basis']}",
            "supplier_id": prod_ticket["supplier_id"],
            "property_id": prod_ticket["property_id"],
            "destination_id": prod_ticket["destination_id"],
            "origin_destination_id": prod_ticket["origin_destination_id"],
            "supplier_product_name": prod_ticket["supplier_product_name"],
        })

        # 3.7 Meal Product
        meal_payload = {
            "destination_id": "dst_ha-noi",
            "category": "meal",
            "subcategory": "fine_dining",
            "title": "Fine Dining Tasting Menu at Gia Hanoi",
            "supplier_product_name": "Seasonal Discovery Tasting Menu (8 courses)",
            "unit": "person",
            "time_basis": "trip",
            "category_attributes": {"meal_type": "dinner", "cuisine": "contemporary_vietnamese"},
        }
        res_meal = client.post("/api/v2/products", json=meal_payload)
        assert res_meal.status_code == 201
        prod_meal = res_meal.json()
        results["fixtures_created"].append({
            "fixture": "Meal / Dining Product",
            "id": prod_meal["id"],
            "title": prod_meal["title"],
            "category": prod_meal["category"],
            "subcategory": prod_meal["subcategory"],
            "unit_x_time_basis": f"{prod_meal['unit']} × {prod_meal['time_basis']}",
            "supplier_id": prod_meal["supplier_id"],
            "property_id": prod_meal["property_id"],
            "destination_id": prod_meal["destination_id"],
            "origin_destination_id": prod_meal["origin_destination_id"],
            "supplier_product_name": prod_meal["supplier_product_name"],
        })

        # 3.8 Visa Product
        visa_payload = {
            "destination_id": "dst_ha-noi",
            "category": "visa",
            "subcategory": "urgent_visa",
            "title": "Vietnam E-Visa Expedited 24h Processing",
            "supplier_product_name": "Express 24-Hour Vietnam Tourist E-Visa Approval",
            "unit": "visa_case",
            "time_basis": "trip",
            "category_attributes": {"visa_type": "e_visa_30d_single", "processing_days": 1},
        }
        res_visa = client.post("/api/v2/products", json=visa_payload)
        assert res_visa.status_code == 201
        prod_visa = res_visa.json()
        results["fixtures_created"].append({
            "fixture": "Visa / Legal Product",
            "id": prod_visa["id"],
            "title": prod_visa["title"],
            "category": prod_visa["category"],
            "subcategory": prod_visa["subcategory"],
            "unit_x_time_basis": f"{prod_visa['unit']} × {prod_visa['time_basis']}",
            "supplier_id": prod_visa["supplier_id"],
            "property_id": prod_visa["property_id"],
            "destination_id": prod_visa["destination_id"],
            "origin_destination_id": prod_visa["origin_destination_id"],
            "supplier_product_name": prod_visa["supplier_product_name"],
        })

        # 3.9 Guide Expense Product
        gexp_payload = {
            "destination_id": "dst_quang-ninh",
            "category": "guide_expense",
            "subcategory": "guide_allowance",
            "title": "Guide Overnight Allowance Halong",
            "supplier_product_name": "Overnight Outstation Guide Per Diem",
            "unit": "group",
            "time_basis": "day",
            "category_attributes": {"expense_type": "allowance_outstation"},
        }
        res_gexp = client.post("/api/v2/products", json=gexp_payload)
        assert res_gexp.status_code == 201
        prod_gexp = res_gexp.json()
        results["fixtures_created"].append({
            "fixture": "Guide Expense Product",
            "id": prod_gexp["id"],
            "title": prod_gexp["title"],
            "category": prod_gexp["category"],
            "subcategory": prod_gexp["subcategory"],
            "unit_x_time_basis": f"{prod_gexp['unit']} × {prod_gexp['time_basis']}",
            "supplier_id": prod_gexp["supplier_id"],
            "property_id": prod_gexp["property_id"],
            "destination_id": prod_gexp["destination_id"],
            "origin_destination_id": prod_gexp["origin_destination_id"],
            "supplier_product_name": prod_gexp["supplier_product_name"],
        })

        # 3.10 Others Product
        other_payload = {
            "destination_id": "dst_ha-noi",
            "category": "others",
            "subcategory": "airport_fast_track",
            "title": "Noi Bai Airport VIP Fast Track & Porterage",
            "supplier_product_name": "Arrival Fast Track Service with Dedicated Immigration Line",
            "unit": "person",
            "time_basis": "trip",
            "category_attributes": {"terminal": "international_t2", "has_buggy": True},
        }
        res_other = client.post("/api/v2/products", json=other_payload)
        assert res_other.status_code == 201
        prod_other = res_other.json()
        results["fixtures_created"].append({
            "fixture": "Ancillary / Others Product",
            "id": prod_other["id"],
            "title": prod_other["title"],
            "category": prod_other["category"],
            "subcategory": prod_other["subcategory"],
            "unit_x_time_basis": f"{prod_other['unit']} × {prod_other['time_basis']}",
            "supplier_id": prod_other["supplier_id"],
            "property_id": prod_other["property_id"],
            "destination_id": prod_other["destination_id"],
            "origin_destination_id": prod_other["origin_destination_id"],
            "supplier_product_name": prod_other["supplier_product_name"],
        })

        # -------------------------------------------------------------
        # STEP 4: Invariant & Constraint Boundary Assertions
        # -------------------------------------------------------------

        # Invariant 4.1: Immutable supplier_product_name
        # Test PUT updating title -> works, supplier_product_name unchanged
        update_title_res = client.put(
            f"/api/v2/products/{prod_acc['id']}",
            json={"title": "Metropole Grand Luxury Room (Heritage Wing Renovated)"}
        )
        assert update_title_res.status_code == 200
        assert update_title_res.json()["supplier_product_name"] == prod_acc["supplier_product_name"]
        assert update_title_res.json()["title"] == "Metropole Grand Luxury Room (Heritage Wing Renovated)"
        results["invariants_tested"].append({
            "invariant": "Immutable supplier_product_name (Safe Title Update)",
            "test": "Update title via PUT without touching supplier_product_name",
            "result": "PASSED - Title updated while source fact remained untouched",
        })

        # Test PUT modifying supplier_product_name -> rejected with 422
        bad_update_res = client.put(
            f"/api/v2/products/{prod_acc['id']}",
            json={"supplier_product_name": "Tampered Supplier Product Name"}
        )
        assert bad_update_res.status_code == 422, f"Expected 422, got {bad_update_res.status_code}"
        results["invariants_tested"].append({
            "invariant": "Immutable supplier_product_name (Tamper Prevention)",
            "test": "Attempt to change supplier_product_name via PUT payload",
            "result": f"PASSED - Rejected with HTTP {bad_update_res.status_code} ({bad_update_res.json()['detail']})",
        })

        # Invariant 4.2: Content Separation (R4)
        # property_id rejected if category != accommodation
        bad_prop_res = client.post(
            "/api/v2/products",
            json={
                "destination_id": "dst_ha-noi",
                "category": "transportation",
                "property_id": "acc_metropole_hanoi",
                "title": "Invalid Transport with Property ID",
            }
        )
        assert bad_prop_res.status_code == 422
        results["invariants_tested"].append({
            "invariant": "Content Separation R4 (Property ID category constraint)",
            "test": "Attempt to set property_id on transportation product",
            "result": "PASSED - Rejected with HTTP 422 (property_id only allowed when category == 'accommodation')",
        })

        # Invariant 4.3: Origin Destination Category Constraint
        bad_origin_res = client.post(
            "/api/v2/products",
            json={
                "destination_id": "dst_ha-noi",
                "origin_destination_id": "dst_quang-ninh",
                "category": "experience",
                "title": "Invalid Experience with Origin Destination",
            }
        )
        assert bad_origin_res.status_code == 422
        results["invariants_tested"].append({
            "invariant": "Origin Destination Constraint (15.2b §3.4)",
            "test": "Attempt to set origin_destination_id on experience category",
            "result": "PASSED - Rejected with HTTP 422 (only transportation/flights allowed)",
        })

        # Invariant 4.4: Subcategory Vocab Boundary
        bad_subcat_res = client.post(
            "/api/v2/products",
            json={
                "destination_id": "dst_ha-noi",
                "category": "accommodation",
                "subcategory": "car_4_seat",  # belongs to transportation, not accommodation
                "title": "Invalid Accommodation with Car Subcategory",
            }
        )
        assert bad_subcat_res.status_code == 422
        results["invariants_tested"].append({
            "invariant": "Closed Subcategory Vocab Matrix",
            "test": "Attempt to assign transportation subcategory to accommodation product",
            "result": f"PASSED - Rejected with HTTP 422 ({bad_subcat_res.json()['detail']})",
        })

        # Invariant 4.5: Subcategory note requires other_*
        bad_note_res = client.post(
            "/api/v2/products",
            json={
                "destination_id": "dst_ha-noi",
                "category": "accommodation",
                "subcategory": "hotel",
                "subcategory_note": "Orphan Note",
                "title": "Invalid Hotel with Subcategory Note",
            }
        )
        assert bad_note_res.status_code == 422
        results["invariants_tested"].append({
            "invariant": "Subcategory Note Safety Guard",
            "test": "Attempt to supply subcategory_note for non-other subcategory",
            "result": "PASSED - Rejected with HTTP 422 (only allowed for other_* subcategories)",
        })

        # Invariant 4.6: Unique Functional Index with Origin Destination
        # Same title 'Private Van Transfer' allowed on different route
        trans2_res = client.post(
            "/api/v2/products",
            json={
                "supplier_id": "sup_capella_transport",
                "destination_id": "dst_da-nang",
                "origin_destination_id": "dst_ha-noi",
                "category": "transportation",
                "subcategory": "van_16_seat",
                "title": "Private Van Transfer Hanoi - Halong",  # Same title, different destination!
            }
        )
        assert trans2_res.status_code == 201, f"Expected 201 on different route: {trans2_res.text}"
        results["invariants_tested"].append({
            "invariant": "Point-to-Point Unique Functional Index",
            "test": "Create same-titled transport product with different destination_id",
            "result": "PASSED - Successfully created without unique index collision",
        })

        # -------------------------------------------------------------
        # STEP 5: Destination Tourism Hub Hierarchy & Merge Verification
        # -------------------------------------------------------------
        # Check single destination query
        hanoi_res = client.get("/api/v2/destinations/dst_ha-noi")
        assert hanoi_res.status_code == 200
        hanoi_hub = hanoi_res.json()
        assert hanoi_hub["destinationType"] == "city"
        assert hanoi_hub["timezone"] == "Asia/Ho_Chi_Minh"
        assert hanoi_hub["parentId"] == "dst_country_vietnam"

        dest_name = hanoi_hub.get("name") or hanoi_hub.get("canonicalName") or "Hanoi"
        results["destination_tested"].append({
            "feature": "Tourism Hub Attributes",
            "destination": f"{dest_name} ({hanoi_hub['id']})",
            "type": hanoi_hub["destinationType"],
            "timezone": hanoi_hub["timezone"],
            "parent_id": hanoi_hub["parentId"],
            "status": "PASSED",
        })

        # Test Destination Merge (15.2b §3.2)
        # Create a deprecated hub to merge
        legacy_hub_res = client.post(
            "/api/v2/destinations",
            json={
                "canonicalName": "Ha Tay Historic Province",
                "slug": "ha-tay",
                "countrySlug": "vietnam",
                "latitude": 20.85,
                "longitude": 105.75,
                "aliases": ["Ha Tay", "Ha Dong", "Son Tay"],
            }
        )
        assert legacy_hub_res.status_code == 201
        legacy_hub = legacy_hub_res.json()

        # Merge Ha Tay -> Hanoi
        merge_res = client.post(f"/api/v2/destinations/{legacy_hub['id']}/merge", json={"targetId": "dst_ha-noi"})
        assert merge_res.status_code == 200
        merged_doc = merge_res.json()
        assert merged_doc["mergedIntoId"] == "dst_ha-noi"
        assert merged_doc["isActive"] is False

        # Verify search for merged alias returns target hub with matchedFrom
        search_res = client.get("/api/v2/destinations?query=ha%20tay")
        assert search_res.status_code == 200
        search_items = search_res.json()["items"]
        assert len(search_items) >= 1
        assert any(item["id"] == "dst_ha-noi" for item in search_items)

        legacy_name = legacy_hub.get("name") or legacy_hub.get("canonicalName") or "Ha Tay"
        results["destination_tested"].append({
            "feature": "Destination Merge & Soft Redirect",
            "source": f"{legacy_name} ({legacy_hub['id']})",
            "target": "Hanoi (dst_ha-noi)",
            "merged_into_id": merged_doc["mergedIntoId"],
            "is_active": merged_doc["isActive"],
            "alias_redirection": "PASSED - Resolving 'Ha Tay' returns 'dst_ha-noi'",
        })

        # Summary Matrix
        results["summary"] = {
            "total_products_created": len(results["fixtures_created"]),
            "invariants_passed": len(results["invariants_tested"]),
            "destination_tests_passed": len(results["destination_tested"]),
            "all_passed": True,
        }

        print("=== VERIFICATION RESULTS JSON ===")
        print(json.dumps(results, indent=2))
        return results

    finally:
        session_patch1.stop()
        session_patch2.stop()
        auth_patch.stop()
        await engine.dispose()
        os.unlink(temp_db.name)

if __name__ == "__main__":
    asyncio.run(run_verification())

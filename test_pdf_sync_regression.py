import asyncio
import copy
import json
import re
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient


class _FakeAgent:
    def __init__(self, *args, **kwargs):
        pass


fake_pydantic_ai = types.ModuleType("pydantic_ai")
fake_pydantic_ai.Agent = _FakeAgent
sys.modules.setdefault("pydantic_ai", fake_pydantic_ai)

fake_llm_client = types.ModuleType("llm_client")
fake_llm_client.get_model = lambda: None
sys.modules.setdefault("llm_client", fake_llm_client)

from main import app, _render_quotation_doc_from_ctx, _save_ctx_html_sync_state


client = TestClient(app)


def replace_editable_value(html: str, field: str, new_value: str) -> str:
    pattern = rf'(<[^>]+data-editable="{re.escape(field)}"[^>]*>)(.*?)(</[^>]+>)'
    updated_html, count = re.subn(pattern, rf"\1{new_value}\3", html, count=1, flags=re.DOTALL)
    if count != 1:
        raise AssertionError(f"Editable field '{field}' not found")
    return updated_html


def build_regression_payload() -> dict:
    payload = json.loads(
        Path("published/quo_d8bbe1c59a8a/payload.json").read_text(encoding="utf-8")
    )
    payload["quotationNumber"] = "QT-2026-DRIFT-LOCK"
    return payload


def test_publish_syncs_composite_fields_into_pdf():
    payload = build_regression_payload()

    create_res = client.post("/quotations", json=payload)
    assert create_res.status_code == 200, create_res.text
    quotation_id = create_res.json()["quotationId"]

    html_res = client.get(f"/quotations/{quotation_id}")
    assert html_res.status_code == 200, html_res.text
    edited_html = html_res.text

    edited_html = replace_editable_value(
        edited_html,
        "hero_meta_1",
        "14 DAYS • 13 NIGHTS • luxury boutique",
    )
    edited_html = replace_editable_value(
        edited_html,
        "letter_greeting",
        "Dear <strong>Tina &amp; Friends</strong>,",
    )
    edited_html = replace_editable_value(
        edited_html,
        "letter_intro",
        (
            "I am delighted to present this privately arranged journey: "
            "<strong>Tina’s Vietnam Birthday Escape</strong>, created for "
            "<strong>11 passengers</strong> travelling from <strong>27 Mar – 09 Apr 2027</strong>. "
            "The route unfolds from <strong>Hanoi – Ninh Binh – Halong Bay – Hoi An – Da Nang – Hue – Ho Chi Minh City</strong>."
        ),
    )
    edited_html = replace_editable_value(
        edited_html,
        "letter_body_p2",
        (
            "The programme has been considered around a gentler family rhythm: early "
            "check-in in Hanoi, private guiding and transfers, a luxury overnight cruise, "
            "and enough space between active days to pause."
        ),
    )
    edited_html = replace_editable_value(
        edited_html,
        "letter_outro",
        "Please review the journey as a starting point for a personal conversation. Every final detail can be refined around your preferred pace, room choices, and priorities.",
    )
    edited_html = replace_editable_value(edited_html, "letter_sign_off", "Eddie")
    edited_html = replace_editable_value(edited_html, "seller_email", "sales@capellatravel.com")
    edited_html = replace_editable_value(edited_html, "contact_phone", "+84 913 393 119")
    edited_html = replace_editable_value(
        edited_html,
        "footer_text",
        "Capella Travel - Tina’s Vietnam Birthday Escape",
    )
    edited_html = replace_editable_value(
        edited_html,
        "hotel_intro_1",
        "Peridot Grand Luxury Boutique Hotel offers an oasis of tranquility in the heart of Hanoi's Old Quarter.<div><br></div><div><b>Room type: </b>Grand Deluxe</div>",
    )
    edited_html = replace_editable_value(
        edited_html,
        "hotel_intro_3",
        "Anantara Hoi An Resort is a boutique retreat on the banks of the Thu Bon River.<div><br></div><div><b>Room type: </b>Deluxe Balcony</div>",
    )
    edited_html = replace_editable_value(
        edited_html,
        "hotel_intro_4",
        "Hyatt Regency Danang Resort and Spa is a luxury beachfront resort with sweeping ocean views.<div><br></div><div><b>Room type: </b>3 Bedroom Beach Front Pool Villa</div>",
    )

    publish_res = client.post(f"/quotations/{quotation_id}/publish", json={"html": edited_html})
    assert publish_res.status_code == 200, publish_res.text

    quo_dir = Path("published") / quotation_id
    ctx_data = json.loads((quo_dir / "ctx.json").read_text(encoding="utf-8"))
    html_sync = ctx_data["html_sync"]["en"]
    assert html_sync["captured_from_version"] == 2
    assert html_sync["composite_fields"]["hotels"]["1"]["room_type"] == "Grand Deluxe"
    assert html_sync["composite_fields"]["hotels"]["3"]["room_type"] == "Deluxe Balcony"
    assert html_sync["composite_fields"]["hotels"]["4"]["room_type"] == "3 Bedroom Beach Front Pool Villa"

    pdf_res = client.get(f"/quotations/{quotation_id}/pdf")
    assert pdf_res.status_code == 200, pdf_res.text
    pdf_html = pdf_res.text
    for expected in [
        "11 passengers",
        "luxury overnight cruise",
        "Eddie",
        "sales@capellatravel.com",
        "Grand Deluxe",
        "Deluxe Balcony",
        "3 Bedroom Beach Front Pool Villa",
    ]:
        assert expected in pdf_html


def test_v19_fixture_rerender_removes_legacy_pdf_fallbacks():
    quo_dir = Path("published/quo_d8bbe1c59a8a")
    ctx_data = json.loads((quo_dir / "ctx.json").read_text(encoding="utf-8"))
    ctx_data = copy.deepcopy(ctx_data)
    v19_html = (quo_dir / "v19.html").read_text(encoding="utf-8")

    _save_ctx_html_sync_state(ctx_data, "en", v19_html, captured_from_version=19)
    rendered_pdf, _ = asyncio.run(
        _render_quotation_doc_from_ctx(
            ctx_data,
            "quo_d8bbe1c59a8a",
            "en",
            request=None,
            is_pdf=True,
        )
    )

    for expected in [
        "11 passengers",
        "Hanoi – Ninh Binh – Halong Bay – Hoi An – Da Nang – Hue – Ho Chi Minh City",
        "luxury overnight cruise",
        "Eddie",
        "sales@capellatravel.com",
        "Grand Deluxe",
        "Deluxe Balcony",
        "3 Bedroom Beach Front Pool Villa",
    ]:
        assert expected in rendered_pdf

    for unexpected in [
        "PROGRAM OVERVIEW",
        "VIP Family",
        "Anh Son Le",
        "sales@vietnamsafar.vn",
    ]:
        assert unexpected not in rendered_pdf

    assert rendered_pdf.count("Deluxe Room") < 5


def test_v22_fixture_rerender_keeps_runtime_itinerary_edits_in_pdf():
    quo_dir = Path("published/quo_d8bbe1c59a8a")
    ctx_data = json.loads((quo_dir / "ctx.json").read_text(encoding="utf-8"))
    ctx_data = copy.deepcopy(ctx_data)
    v22_html = (quo_dir / "v22.html").read_text(encoding="utf-8")

    _save_ctx_html_sync_state(ctx_data, "en", v22_html, captured_from_version=22)
    rendered_pdf, _ = asyncio.run(
        _render_quotation_doc_from_ctx(
            ctx_data,
            "quo_d8bbe1c59a8a",
            "en",
            request=None,
            is_pdf=True,
        )
    )

    for expected in [
        "dedicated concierge member",
        "Dinner, Lunch subjects to arrival time",
        "while some of the members say goodbye to Vietnam, the other continue their journey",
        "two spectacular 3-Bedroom Beach Front Pool Villas",
        "meeting exclusively with a war veteran",
        "Breakfast, Lunch, Dinner on board",
    ]:
        assert expected in rendered_pdf

    for unexpected in [
        "Guests will then check into a spectacular 3-Bedroom Beach Front Pool Villa",
    ]:
        assert unexpected not in rendered_pdf

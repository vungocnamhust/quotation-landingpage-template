import main


def test_landing_booking_terms_sync_to_pdf_term_fields_as_rich_text():
    lang_ctx = {
        "booking_terms": [
            {"label": "Deposit", "body": "Old deposit"},
            {"label": "Balance", "body": "Old balance"},
            {"label": "Cancellation", "body": "Old cancellation"},
        ],
        "term_deposit": "Old deposit",
        "term_balance": "Old balance",
        "term_cancellation": "Old cancellation",
        "itinerary": [],
        "itinerary_days": [],
        "hotels": [],
        "inclusions": [],
        "exclusions": [],
    }
    edited_fields = {
        "booking_term_label_0": "Deposit",
        "booking_term_body_0": "<ul><li>30% non-refundable deposit.</li><li>100% within 60 days.</li></ul>",
        "booking_term_body_2": "<div>Written notice required.</div><ul><li>30 days prior: 75%</li></ul>",
    }

    main.filter_and_override_ctx(
        lang_ctx,
        set(edited_fields),
        edited_fields,
        override_text=True,
    )

    assert lang_ctx["term_deposit"] == edited_fields["booking_term_body_0"]
    assert lang_ctx["term_cancellation"] == edited_fields["booking_term_body_2"]
    assert lang_ctx["booking_terms"][0]["body"] == edited_fields["booking_term_body_0"]
    assert lang_ctx["booking_terms"][2]["body"] == edited_fields["booking_term_body_2"]
    assert "<li>" in lang_ctx["term_deposit"]


def test_html_parser_preserves_booking_term_list_markup_for_pdf_sync():
    lang_ctx = {
        "booking_terms": [{"label": "Deposit", "body": "Old deposit"}],
        "term_deposit": "Old deposit",
        "itinerary": [],
        "itinerary_days": [],
        "hotels": [],
        "inclusions": [],
        "exclusions": [],
    }
    html = """
    <div data-editable="booking_term_label_0">Deposit</div>
    <div data-editable="booking_term_body_0"><ul><li>First payment line</li><li>Second payment line</li></ul></div>
    """

    main.filter_and_override_ctx_by_html(lang_ctx, html, override_text=True)

    assert lang_ctx["term_deposit"] == "<ul><li>First payment line</li><li>Second payment line</li></ul>"
    assert lang_ctx["booking_terms"][0]["body"] == lang_ctx["term_deposit"]


def test_pdf_confirmation_row_is_not_rendered_when_term_is_empty():
    source, _, _ = main.templates.env.loader.get_source(
        main.templates.env,
        "prototype_itinerary_imagery_pdf.html",
    )

    assert "{% if term_confirmation %}" in source
    assert "{{ term_confirmation | safe }}" in source

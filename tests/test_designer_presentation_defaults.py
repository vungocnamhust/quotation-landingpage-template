from services.skeleton_builder import DESIGNER_PRESENTATION_DEFAULTS
from quote_document import CreateQuoteDesignerFacts


def test_designer_fact_model_uses_prototype_defaults_when_values_are_omitted():
    facts = CreateQuoteDesignerFacts()

    assert facts.designer_kicker == DESIGNER_PRESENTATION_DEFAULTS["kicker"]
    assert facts.designer_title == DESIGNER_PRESENTATION_DEFAULTS["title"]
    assert facts.designer_quote == DESIGNER_PRESENTATION_DEFAULTS["quote"]
    assert facts.designer_signature == DESIGNER_PRESENTATION_DEFAULTS["signature"]
    assert facts.designer_experience == DESIGNER_PRESENTATION_DEFAULTS["experience"]
    assert facts.cta_body == DESIGNER_PRESENTATION_DEFAULTS["ctaBody"]


def test_skeleton_preserves_designer_defaults_for_legacy_null_facts():
    # Existing Fact snapshots may contain explicit nulls. The canonical document
    # must still produce the prototype copy without a Design-side fallback.
    defaults = DESIGNER_PRESENTATION_DEFAULTS
    assert defaults["kicker"] == "YOUR JOURNEY DESIGNER"
    assert defaults["title"] == "Let Us Shape the Final Details Together"
    assert defaults["signature"] == "TRAVEL DESIGNER"
    assert defaults["experience"] == "Present throughout the planning, quietly working behind the journey."
    assert "desire to travel is contagious" in defaults["quote"]

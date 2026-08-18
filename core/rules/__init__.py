"""Clean Architecture Business Rules & Gatekeeper Pipeline for Bespoke Luxury Travel."""

from core.rules.base import BusinessGate, GateIssue, GateResult, Severity
from core.rules.dates_rules import (
    calculate_duration,
    date_for_itinerary_day,
    format_travel_dates_label,
    parse_iso_date,
)
from core.rules.field_ownership_rules import (
    BRAND_PROTECTED_FIELDS,
    CONTENT_FIELDS,
    DESIGN_FIELDS,
    FACTS_FIELDS,
    FieldOwnershipGate,
    FieldPartition,
)
from core.rules.party_rules import (
    generate_party_label,
    infer_greeting_name,
    resolve_client_display_name,
)
from core.rules.pricing_rules import (
    SUPPORTED_CURRENCIES,
    apply_child_preset_ratio,
    calculate_tri_pricing,
    currency_divisor,
    infer_rates_from_group_total,
    parse_legacy_amount_minor,
)
from core.rules.quotation_rules import QuotationTransitionGate
from core.rules.readiness_rules import PublishReadinessGate
from core.rules.request_rules import RequestIntakeGate
from core.rules.service_candidate_rules import (
    ServiceCandidate,
    ServiceCandidateEvaluator,
    ServiceType,
)
from core.rules.stays_rules import (
    consolidate_stays_from_day_accommodations,
    validate_hotel_boundaries,
)
from core.rules.taxonomy_rules import (
    MULTILINGUAL_DEFAULT_MEALS,
    get_default_meals_for_lang,
    infer_default_currency,
    sync_travel_style_facts,
)

__all__ = [
    # Base
    "Severity",
    "GateIssue",
    "GateResult",
    "BusinessGate",
    # Dates
    "parse_iso_date",
    "calculate_duration",
    "date_for_itinerary_day",
    "format_travel_dates_label",
    # Stays
    "consolidate_stays_from_day_accommodations",
    "validate_hotel_boundaries",
    # Pricing
    "SUPPORTED_CURRENCIES",
    "currency_divisor",
    "parse_legacy_amount_minor",
    "calculate_tri_pricing",
    "apply_child_preset_ratio",
    "infer_rates_from_group_total",
    # Party
    "resolve_client_display_name",
    "generate_party_label",
    "infer_greeting_name",
    # Taxonomy
    "MULTILINGUAL_DEFAULT_MEALS",
    "get_default_meals_for_lang",
    "sync_travel_style_facts",
    "infer_default_currency",
    # Field Ownership
    "FieldPartition",
    "FACTS_FIELDS",
    "CONTENT_FIELDS",
    "DESIGN_FIELDS",
    "BRAND_PROTECTED_FIELDS",
    "FieldOwnershipGate",
    # Gatekeepers
    "RequestIntakeGate",
    "QuotationTransitionGate",
    "PublishReadinessGate",
    # Service Candidate Protocol
    "ServiceType",
    "ServiceCandidate",
    "ServiceCandidateEvaluator",
]

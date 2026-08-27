"""Gate 5 (Future Scope): Service Candidate Choosing & Supplier Scoring Protocol.

``ServiceType`` mirrors the 10-value ``CATEGORY`` vocab in ``catalog_vocab.py``
(15.2 §1.6) — rail/cruise are ``transportation`` subcategories, per Tourplan's
Service Type code table + option code convention. No second taxonomy exists.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from core.rules.catalog_vocab import CATEGORY


class ServiceType(str, Enum):
    ACCOMMODATION = "accommodation"
    TRANSPORTATION = "transportation"
    TICKET = "ticket"
    FLIGHTS = "flights"
    GUIDE = "guide"
    GUIDE_EXPENSE = "guide_expense"
    EXPERIENCE = "experience"
    MEAL = "meal"
    VISA = "visa"
    OTHERS = "others"


assert {member.value for member in ServiceType} == CATEGORY  # keep in sync with catalog_vocab.py


@dataclass
class ServiceCandidate:
    id: str
    service_type: ServiceType
    name: str
    destination: str
    tier: str  # e.g. "luxury", "ultra_luxury", "boutique"
    score: float  # 0.0 to 1.0
    reasoning: list[str] = field(default_factory=list)
    is_available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class ServiceCandidateEvaluator(Protocol):
    """Protocol for ranking candidate services for a given itinerary day."""

    def evaluate_candidates(
        self,
        destination: str,
        party_size: int,
        travel_style: str | None,
        constraints: dict[str, Any] | None = None,
    ) -> list[ServiceCandidate]:
        ...

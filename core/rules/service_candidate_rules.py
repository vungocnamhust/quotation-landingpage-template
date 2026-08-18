"""Gate 5 (Future Scope): Service Candidate Choosing & Supplier Scoring Protocol."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class ServiceType(str, Enum):
    ACCOMMODATION = "accommodation"
    RAIL = "rail"
    CRUISE = "cruise"
    TRANSPORT = "transport"
    EXPERIENCE = "experience"
    GUIDE = "guide"


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

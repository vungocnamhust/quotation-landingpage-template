"""Base definitions for Business Rule Gates in Bespoke Travel Architecture."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, TypeVar


class Severity(str, Enum):
    ERROR = "error"  # Blocks transition or save
    WARNING = "warning"  # Allows transition but warns user/staff
    INFO = "info"  # Helpful suggestion or auto-derivation context


@dataclass(frozen=True)
class GateIssue:
    field: str
    code: str
    message: str
    severity: Severity = Severity.ERROR
    suggestion: str | None = None


@dataclass
class GateResult:
    passed: bool
    issues: list[GateIssue] = field(default_factory=list)
    derived_data: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[GateIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[GateIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def infos(self) -> list[GateIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO]


TContext = TypeVar("TContext", contravariant=True)


class BusinessGate(Protocol[TContext]):
    """Protocol for business validation and gatekeeping."""

    def evaluate(self, context: TContext) -> GateResult:
        ...

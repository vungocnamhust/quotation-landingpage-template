"""K4 — actor attribution for writes performed by staff or automated agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ActorType = Literal["staff", "ai_agent", "system"]


@dataclass(frozen=True)
class ActorRef:
    actor_id: str
    actor_type: ActorType

    def serialize(self) -> str:
        return f"{self.actor_type}:{self.actor_id}"

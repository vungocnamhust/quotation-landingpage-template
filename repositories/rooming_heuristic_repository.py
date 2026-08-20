from __future__ import annotations

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.rooming_heuristic import RoomingHeuristicRule


class RoomingHeuristicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> list[RoomingHeuristicRule]:
        stmt = (
            select(RoomingHeuristicRule)
            .where(RoomingHeuristicRule.is_active.is_(True))
            .order_by(RoomingHeuristicRule.priority.desc(), RoomingHeuristicRule.id.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_all(self) -> list[RoomingHeuristicRule]:
        stmt = (
            select(RoomingHeuristicRule)
            .order_by(RoomingHeuristicRule.priority.desc(), RoomingHeuristicRule.id.asc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get(self, rule_id: str) -> RoomingHeuristicRule | None:
        return await self.session.get(RoomingHeuristicRule, rule_id)

    async def upsert(
        self,
        *,
        rule_id: str,
        name: str,
        description: str | None = None,
        min_adults: int = 1,
        max_adults: int | None = None,
        min_children: int = 0,
        max_children: int | None = None,
        min_infants: int = 0,
        max_infants: int | None = None,
        kid_age_condition: str = "ANY",
        suggestions: list[dict[str, Any]],
        min_rooms_formula: str | None = None,
        priority: int = 0,
        is_active: bool = True,
    ) -> RoomingHeuristicRule:
        rule = await self.session.get(RoomingHeuristicRule, rule_id)
        if rule is None:
            rule = RoomingHeuristicRule(
                id=rule_id,
                name=name,
                description=description,
                min_adults=min_adults,
                max_adults=max_adults,
                min_children=min_children,
                max_children=max_children,
                min_infants=min_infants,
                max_infants=max_infants,
                kid_age_condition=kid_age_condition,
                suggestions=suggestions,
                min_rooms_formula=min_rooms_formula,
                priority=priority,
                is_active=is_active,
            )
            self.session.add(rule)
        else:
            rule.name = name
            rule.description = description
            rule.min_adults = min_adults
            rule.max_adults = max_adults
            rule.min_children = min_children
            rule.max_children = max_children
            rule.min_infants = min_infants
            rule.max_infants = max_infants
            rule.kid_age_condition = kid_age_condition
            rule.suggestions = suggestions
            rule.min_rooms_formula = min_rooms_formula
            rule.priority = priority
            rule.is_active = is_active

        await self.session.flush()
        return rule

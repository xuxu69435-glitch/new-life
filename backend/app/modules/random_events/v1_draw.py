from typing import Any

from app.engine.simulation_context import LifeState
from app.infrastructure.rng import ServerRandom
from app.modules.random_events.condition_matcher import RandomEventConditionMatcher
from app.modules.random_events.library_models import V1EventDefinition


class RandomEventV1DrawService:
    def __init__(self, matcher: RandomEventConditionMatcher | None = None) -> None:
        self.matcher = matcher or RandomEventConditionMatcher()

    def eligible_social_events(
        self,
        events: list[V1EventDefinition],
        state: LifeState,
        event_history: dict[str, Any],
        *,
        blocked_sub_categories: set[str] | None = None,
    ) -> list[V1EventDefinition]:
        eligible: list[V1EventDefinition] = []
        blocked = blocked_sub_categories or set()
        for event in events:
            if event.pool_type != "social":
                continue
            if not event.is_drawable():
                continue
            sub_category = str(getattr(event, "sub_category", "") or event.conditions.get("sub_category", ""))
            if sub_category in blocked:
                continue
            if not self.matcher.matches(event, state):
                continue
            if not self._repeat_allowed(event, state.age, event_history):
                continue
            if event.weight <= 0:
                continue
            eligible.append(event)
        return eligible

    def eligible_normal_events(
        self,
        events: list[V1EventDefinition],
        state: LifeState,
        event_history: dict[str, Any],
    ) -> list[V1EventDefinition]:
        eligible: list[V1EventDefinition] = []
        for event in events:
            if event.pool_type != "normal":
                continue
            if not event.is_drawable():
                continue
            if not self.matcher.matches(event, state):
                continue
            if not self._repeat_allowed(event, state.age, event_history):
                continue
            if event.weight <= 0:
                continue
            eligible.append(event)
        return eligible

    def eligible_direct_death_events(
        self,
        events: list[V1EventDefinition],
        state: LifeState,
        event_history: dict[str, Any],
    ) -> list[V1EventDefinition]:
        eligible: list[V1EventDefinition] = []
        for event in events:
            if event.pool_type != "direct_death":
                continue
            if event.implementation_status == "planned":
                continue
            if not self.matcher.matches(event, state):
                continue
            if not self._repeat_allowed(event, state.age, event_history):
                continue
            if event.weight <= 0:
                continue
            eligible.append(event)
        return eligible

    def draw_by_weight(
        self,
        pool: list[V1EventDefinition],
        rng: ServerRandom,
    ) -> V1EventDefinition | None:
        if not pool:
            return None
        total_weight = sum(event.weight for event in pool)
        if total_weight <= 0:
            return None
        roll = rng.random() * total_weight
        cumulative = 0.0
        for event in pool:
            cumulative += event.weight
            if roll <= cumulative:
                return event
        return pool[-1]

    def should_enter_direct_death_pool(
        self,
        limit: float,
        rng: ServerRandom,
    ) -> bool:
        return rng.random() <= limit

    def _repeat_allowed(
        self,
        event: V1EventDefinition,
        current_age: int,
        event_history: dict[str, Any],
    ) -> bool:
        record = event_history.get(event.event_id)
        if event.repeat_policy == "once" and record is not None:
            return False
        if event.repeat_policy == "max_once" and record is not None:
            return False
        if event.repeat_policy == "repeatable" and record is not None:
            cooldown = event.cooldown_years or 0
            last_age = int(record.get("last_age", -999))
            if current_age - last_age < cooldown:
                return False
        return True

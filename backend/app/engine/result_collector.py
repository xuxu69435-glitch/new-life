from typing import Any

from app.engine.simulation_context import LifeState, SimulationEvent, SimulationEventType, YearResult


class ResultCollector:
    def __init__(self) -> None:
        self.changed_attributes: dict[str, int] = {}
        self.changed_health: dict[str, int] = {}
        self.changed_assets: dict[str, float] = {}
        self.life_stage: str | None = None
        self.death_reason: str | None = None
        self.narrative_lines: list[str] = []
        self.inheritance_result: dict[str, Any] | None = None
        self._processed_event_ids: set[int] = set()

    @property
    def death_confirmed(self) -> bool:
        return self.death_reason is not None

    def request_attribute_change(self, key: str, delta: int) -> None:
        self.changed_attributes[key] = self.changed_attributes.get(key, 0) + delta

    def request_health_change(self, key: str, delta: int) -> None:
        self.changed_health[key] = self.changed_health.get(key, 0) + delta

    def request_asset_change(self, key: str, delta: float) -> None:
        self.changed_assets[key] = self.changed_assets.get(key, 0.0) + delta

    def change_life_stage(self, life_stage: str) -> None:
        self.life_stage = life_stage

    def confirm_death(self, reason: str) -> None:
        if self.death_reason is None:
            self.death_reason = reason

    def add_narrative(self, text: str) -> None:
        if text:
            self.narrative_lines.append(text)

    def set_inheritance_result(self, result: dict[str, Any]) -> None:
        self.inheritance_result = result

    def collect_from_events(self, events: list[SimulationEvent]) -> None:
        for index, event in enumerate(events):
            if index in self._processed_event_ids:
                continue
            self._processed_event_ids.add(index)
            payload = event.payload
            if event.event_type == SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED:
                self.request_attribute_change(str(payload["key"]), int(payload.get("delta", 0)))
            elif event.event_type == SimulationEventType.HEALTH_CHANGE_REQUESTED:
                self.request_health_change(str(payload["key"]), int(payload.get("delta", 0)))
            elif event.event_type == SimulationEventType.ASSET_CHANGE_REQUESTED:
                self.request_asset_change(str(payload["key"]), float(payload.get("delta", 0.0)))
            elif event.event_type == SimulationEventType.LIFE_STAGE_CHANGED:
                self.change_life_stage(str(payload["life_stage"]))

    def apply_to_state(self, state: LifeState) -> LifeState:
        next_state = state.model_copy(deep=True)
        next_state.age += 1
        if self.life_stage is not None:
            next_state.life_stage = self.life_stage

        for key, delta in self.changed_attributes.items():
            next_state.attributes[key] = int(next_state.attributes.get(key, 0)) + delta
        for key, delta in self.changed_health.items():
            next_state.health[key] = int(next_state.health.get(key, 0)) + delta
        for key, delta in self.changed_assets.items():
            next_state.assets[key] = float(next_state.assets.get(key, 0.0)) + delta

        if self.death_reason is not None:
            next_state.is_dead = True
            next_state.death_reason = self.death_reason
        return next_state

    def to_year_result(
        self,
        before: LifeState,
        after: LifeState,
        occurred_events: list[SimulationEvent],
        next_available_choices: list[dict[str, Any]],
    ) -> YearResult:
        return YearResult(
            life_id=before.life_id,
            age_before=before.age,
            age_after=after.age,
            is_dead=after.is_dead,
            death_reason=after.death_reason,
            changed_attributes=dict(self.changed_attributes),
            changed_health=dict(self.changed_health),
            changed_assets=dict(self.changed_assets),
            occurred_events=occurred_events,
            narrative_text="\n".join(self.narrative_lines),
            next_available_choices=next_available_choices,
        )

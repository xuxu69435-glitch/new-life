from typing import Any

from app.engine.simulation_context import LifeState, SimulationEvent, SimulationEventType, YearResult
from app.modules.health.sync import apply_post_health_changes


class ResultCollector:
    RANDOM_EVENT_SOURCE = "random_events"

    def __init__(self) -> None:
        self.changed_attributes: dict[str, int] = {}
        self.changed_health: dict[str, int] = {}
        self.changed_assets: dict[str, float] = {}
        self.life_stage: str | None = None
        self.death_reason: str | None = None
        self.death_type: str | None = None
        self.narrative_lines: list[str] = []
        self.inheritance_result: dict[str, Any] | None = None
        self.health_state_update: dict[str, Any] | None = None
        self.health_score_before: int | None = None
        self.health_score_after: int | None = None
        self.health_level_before: str | None = None
        self.health_level_after: str | None = None
        self.new_health_warnings: list[str] = []
        self.natural_death_candidate_created: bool = False
        self.direct_death_candidate_created: bool = False
        self.post_health_changes: dict[str, int] = {}
        self.changed_flags: dict[str, Any] = {}
        self.triggered_random_events: list[dict[str, Any]] = []
        self.random_event_attribute_changes: dict[str, int] = {}
        self.random_event_health_changes: dict[str, int] = {}
        self.random_event_asset_changes: dict[str, float] = {}
        self.education_state_update: dict[str, Any] | None = None
        self.education_stage_before: str | None = None
        self.education_stage_after: str | None = None
        self.education_graduated_this_year: bool = False
        self.career_state_update: dict[str, Any] | None = None
        self.career_status_before: str | None = None
        self.career_status_after: str | None = None
        self.career_path: str | None = None
        self.position_level: str | None = None
        self.annual_income: float = 0.0
        self.career_income_change: float = 0.0
        self.pending_random_event: dict[str, Any] | None = None
        self.unsupported_random_event_effects: list[dict[str, Any]] = []
        self.random_event_choice_result: dict[str, Any] | None = None
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

    def confirm_death(self, reason: str, death_type: str | None = None) -> None:
        if self.death_reason is None:
            self.death_reason = reason
            self.death_type = death_type

    def add_narrative(self, text: str) -> None:
        if text:
            self.narrative_lines.append(text)

    def set_inheritance_result(self, result: dict[str, Any]) -> None:
        self.inheritance_result = result

    def _track_random_event_change(
        self,
        source_module: str,
        category: str,
        key: str,
        delta: int | float,
    ) -> None:
        if source_module != self.RANDOM_EVENT_SOURCE:
            return
        if category == "attribute":
            self.random_event_attribute_changes[key] = int(
                self.random_event_attribute_changes.get(key, 0)
            ) + int(delta)
        elif category == "health":
            self.random_event_health_changes[key] = int(
                self.random_event_health_changes.get(key, 0)
            ) + int(delta)
        elif category == "asset":
            self.random_event_asset_changes[key] = float(
                self.random_event_asset_changes.get(key, 0.0)
            ) + float(delta)

    def collect_from_events(self, events: list[SimulationEvent]) -> None:
        for index, event in enumerate(events):
            if index in self._processed_event_ids:
                continue
            self._processed_event_ids.add(index)
            payload = event.payload
            if event.event_type == SimulationEventType.RANDOM_EVENT_TRIGGERED:
                self.triggered_random_events.append(dict(payload))
            elif event.event_type == SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED:
                key = str(payload["key"])
                delta = int(payload.get("delta", 0))
                self.request_attribute_change(key, delta)
                self._track_random_event_change(event.source_module, "attribute", key, delta)
            elif event.event_type == SimulationEventType.HEALTH_CHANGE_REQUESTED:
                key = str(payload["key"])
                delta = int(payload.get("delta", 0))
                self.request_health_change(key, delta)
                if event.source_module != "health":
                    self.post_health_changes[key] = self.post_health_changes.get(key, 0) + delta
                self._track_random_event_change(event.source_module, "health", key, delta)
            elif event.event_type == SimulationEventType.HEALTH_STATE_UPDATE_REQUESTED:
                self.health_state_update = dict(payload.get("health", {}))
                self.health_score_before = payload.get("health_score_before")
                self.health_score_after = payload.get("health_score_after")
                self.health_level_before = payload.get("health_level_before")
                self.health_level_after = payload.get("health_level_after")
                self.natural_death_candidate_created = bool(
                    payload.get("natural_death_candidate_created", False)
                )
            elif event.event_type == SimulationEventType.HEALTH_WARNING_CREATED:
                warning_text = str(payload.get("text", ""))
                if warning_text:
                    self.new_health_warnings.append(warning_text)
            elif event.event_type == SimulationEventType.ASSET_CHANGE_REQUESTED:
                key = str(payload["key"])
                delta = float(payload.get("delta", 0.0))
                self.request_asset_change(key, delta)
                self._track_random_event_change(event.source_module, "asset", key, delta)
            elif event.event_type == SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED:
                if event.source_module == self.RANDOM_EVENT_SOURCE:
                    self.direct_death_candidate_created = True
            elif event.event_type == SimulationEventType.NARRATIVE_REQUESTED:
                text = str(payload.get("text", ""))
                if text:
                    self.add_narrative(text)
            elif event.event_type == SimulationEventType.FLAG_SET_REQUESTED:
                self.changed_flags[str(payload["key"])] = payload.get("value")
            elif event.event_type == SimulationEventType.EDUCATION_STATE_UPDATE_REQUESTED:
                self.education_state_update = dict(payload.get("education", {}))
                self.education_stage_before = payload.get("education_stage_before")
                self.education_stage_after = payload.get("education_stage_after")
                self.education_graduated_this_year = bool(
                    payload.get("education_graduated_this_year", False)
                )
            elif event.event_type == SimulationEventType.CAREER_STATE_UPDATE_REQUESTED:
                self.career_state_update = dict(payload.get("career", {}))
                self.career_status_before = payload.get("career_status_before")
                self.career_status_after = payload.get("career_status_after")
                self.career_path = payload.get("career_path")
                self.position_level = payload.get("position_level")
                self.annual_income = float(payload.get("annual_income", 0.0))
                self.career_income_change = float(payload.get("career_income_change", 0.0))
            elif event.event_type == SimulationEventType.LIFE_STAGE_CHANGED:
                self.change_life_stage(str(payload["life_stage"]))
            elif event.event_type == SimulationEventType.UNSUPPORTED_EFFECT_RECORDED:
                self.unsupported_random_event_effects.append(dict(payload))
            elif event.event_type == SimulationEventType.RANDOM_EVENT_CHOICE_APPLIED:
                self.random_event_choice_result = dict(payload)

    def apply_to_state(self, state: LifeState, rules: dict | None = None) -> LifeState:
        next_state = state.model_copy(deep=True)
        next_state.age += 1
        if self.life_stage is not None:
            next_state.life_stage = self.life_stage

        for key, delta in self.changed_attributes.items():
            next_state.attributes[key] = int(next_state.attributes.get(key, 0)) + delta

        if self.health_state_update is not None:
            next_state.health = dict(self.health_state_update)
            if self.post_health_changes and rules is not None:
                next_state.health = apply_post_health_changes(
                    next_state.health,
                    self.post_health_changes,
                    rules,
                )
                if "health_score" in self.post_health_changes:
                    self.health_score_after = int(next_state.health.get("health_score", 0))
                    self.health_level_after = str(next_state.health.get("health_level", ""))
        else:
            for key, delta in self.changed_health.items():
                if key == "health_score":
                    next_state.health[key] = int(next_state.health.get(key, 0)) + delta
                else:
                    next_state.health[key] = int(next_state.health.get(key, 0)) + delta

        for key, delta in self.changed_assets.items():
            next_state.assets[key] = float(next_state.assets.get(key, 0.0)) + delta

        from app.modules.assets.models import AssetState

        next_state.assets = AssetState.from_life_state_dict(next_state.assets).to_life_state_dict()

        for key, value in self.changed_flags.items():
            next_state.flags[key] = value

        if self.education_state_update is not None:
            next_state.education = dict(self.education_state_update)
        if self.career_state_update is not None:
            next_state.career = dict(self.career_state_update)

        if self.death_reason is not None:
            next_state.is_dead = True
            next_state.death_reason = self.death_reason

        if self.pending_random_event is not None:
            next_state.pending_random_event = dict(self.pending_random_event)
        if self.random_event_choice_result is not None:
            next_state.pending_random_event = None
        return next_state

    def to_year_result(
        self,
        before: LifeState,
        after: LifeState,
        occurred_events: list[SimulationEvent],
        next_available_choices: list[dict[str, Any]],
    ) -> YearResult:
        health_score_delta = 0
        if self.health_score_before is not None and self.health_score_after is not None:
            health_score_delta = self.health_score_after - self.health_score_before

        return YearResult(
            life_id=before.life_id,
            age_before=before.age,
            age_after=after.age,
            is_dead=after.is_dead,
            death_reason=after.death_reason,
            death_type=self.death_type,
            changed_attributes=dict(self.changed_attributes),
            changed_health=dict(self.changed_health),
            changed_assets=dict(self.changed_assets),
            health_score_before=self.health_score_before,
            health_score_after=self.health_score_after,
            health_level_before=self.health_level_before,
            health_level_after=self.health_level_after,
            health_score_delta=health_score_delta,
            new_health_warnings=list(self.new_health_warnings),
            natural_death_candidate_created=self.natural_death_candidate_created,
            direct_death_candidate_created=self.direct_death_candidate_created,
            triggered_random_events=list(self.triggered_random_events),
            random_event_attribute_changes=dict(self.random_event_attribute_changes),
            random_event_health_changes=dict(self.random_event_health_changes),
            random_event_asset_changes=dict(self.random_event_asset_changes),
            inheritance_result=self.inheritance_result,
            education_stage_before=self.education_stage_before,
            education_stage_after=self.education_stage_after,
            education_graduated_this_year=self.education_graduated_this_year,
            education_changes={
                "stage_before": self.education_stage_before,
                "stage_after": self.education_stage_after,
                "graduated": self.education_graduated_this_year,
            },
            career_status_before=self.career_status_before,
            career_status_after=self.career_status_after,
            career_path=self.career_path,
            position_level=self.position_level,
            annual_income=self.annual_income,
            career_income_change=self.career_income_change,
            occurred_events=occurred_events,
            narrative_text="\n".join(self.narrative_lines),
            next_available_choices=next_available_choices,
            pending_random_event=self.pending_random_event or after.pending_random_event,
            unsupported_random_event_effects=list(self.unsupported_random_event_effects),
            random_event_choice_result=self.random_event_choice_result,
        )

from typing import Any

from app.engine.simulation_context import LifeState, SimulationEvent, SimulationEventType, YearResult
from app.modules.family.events import FamilyEventProcessor
from app.modules.family.models import FamilyState
from app.modules.health.sync import apply_post_health_changes
from app.modules.achievement.models import AchievementState
from app.modules.legal.models import LegalState
from app.modules.mainline.models import MainlineState


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
        self.family_processor = FamilyEventProcessor()
        self._family_working: FamilyState | None = None
        self._family_state_age: int = 0
        self._family_rules: dict[str, Any] | None = None
        self._legal_working: LegalState | None = None
        self.pending_legal_event: dict[str, Any] | None = None
        self.legal_changes: dict[str, Any] = {}
        self._mainline_working: MainlineState | None = None
        self.mainline_changes: dict[str, Any] = {}
        self.completed_mainline_tasks_this_year: list[str] = []
        self.failed_mainline_tasks_this_year: list[str] = []
        self.expired_mainline_tasks_this_year: list[str] = []
        self.mainline_rewards: list[dict[str, Any]] = []
        self.mainline_narrative: list[str] = []
        self.current_guidance_text: str = ""
        self.narrative_result: dict[str, Any] | None = None
        self._achievement_working: AchievementState | None = None
        self.achievement_changes: dict[str, Any] = {}
        self.newly_unlocked_achievements: list[dict[str, Any]] = []
        self.achievement_points_gained: int = 0
        self.milestones_this_year: list[dict[str, Any]] = []
        self.achievement_narrative: list[str] = []
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

    def set_narrative_result(self, result: Any) -> None:
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        self.narrative_result = payload
        summary = str(payload.get("summary_text", ""))
        if summary:
            self.narrative_lines = [summary]

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

    def bind_legal_context(self, state: LifeState) -> None:
        if self._legal_working is None:
            self._legal_working = LegalState.from_life_state_dict(state.legal)

    def bind_mainline_context(self, state: LifeState) -> None:
        if self._mainline_working is None:
            self._mainline_working = MainlineState.from_life_state_dict(state.mainline)

    def bind_achievement_context(self, state: LifeState) -> None:
        if self._achievement_working is None:
            self._achievement_working = AchievementState.from_life_state_dict(state.achievements)

    def snapshot_state(self, state: LifeState, rules: dict | None = None) -> LifeState:
        snapshot = state.model_copy(deep=True)
        snapshot.age += 1
        if self.life_stage is not None:
            snapshot.life_stage = self.life_stage

        for key, delta in self.changed_attributes.items():
            snapshot.attributes[key] = int(snapshot.attributes.get(key, 0)) + delta

        if self.health_state_update is not None:
            snapshot.health = dict(self.health_state_update)
            if self.post_health_changes and rules is not None:
                snapshot.health = apply_post_health_changes(
                    snapshot.health,
                    self.post_health_changes,
                    rules,
                )
        else:
            for key, delta in self.changed_health.items():
                snapshot.health[key] = int(snapshot.health.get(key, 0)) + delta

        for key, delta in self.changed_assets.items():
            snapshot.assets[key] = float(snapshot.assets.get(key, 0.0)) + delta

        from app.modules.assets.models import AssetState

        snapshot.assets = AssetState.from_life_state_dict(snapshot.assets).to_life_state_dict()

        for key, value in self.changed_flags.items():
            snapshot.flags[key] = value

        if self.education_state_update is not None:
            snapshot.education = dict(self.education_state_update)
        if self.career_state_update is not None:
            snapshot.career = dict(self.career_state_update)
        if self._family_working is not None:
            snapshot.family = self._family_working.to_life_state_dict()
        if self._legal_working is not None:
            snapshot.legal = self._legal_working.to_life_state_dict()
        if self._mainline_working is not None:
            snapshot.mainline = self._mainline_working.to_life_state_dict()
        if self._achievement_working is not None:
            snapshot.achievements = self._achievement_working.to_life_state_dict()
        if self.death_reason is not None:
            snapshot.is_dead = True
            snapshot.death_reason = self.death_reason
        return snapshot

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
            elif event.event_type == SimulationEventType.LEGAL_STATE_UPDATE_REQUESTED:
                patch = dict(payload.get("legal", {}))
                if self._legal_working is not None:
                    merged = {**self._legal_working.to_life_state_dict(), **patch}
                    self._legal_working = LegalState.from_life_state_dict(merged)
                    self.legal_changes = merged
            elif event.event_type == SimulationEventType.LEGAL_CHOICE_APPLIED:
                self.legal_changes = dict(payload)
            elif event.event_type == SimulationEventType.MAINLINE_STATE_UPDATE_REQUESTED:
                if self._mainline_working is not None:
                    merged = self._mainline_working.to_life_state_dict()
                    patch = dict(payload.get("mainline", {}))
                    if patch:
                        merged = {**merged, **patch}
                    flags_patch = payload.get("mainline_flags_patch")
                    if flags_patch:
                        merged["mainline_flags"] = {
                            **merged.get("mainline_flags", {}),
                            **dict(flags_patch),
                        }
                    self._mainline_working = MainlineState.from_life_state_dict(merged)
                    self.mainline_changes = merged
                self.completed_mainline_tasks_this_year = list(
                    payload.get("completed_this_year", [])
                )
                self.failed_mainline_tasks_this_year = list(payload.get("failed_this_year", []))
                self.expired_mainline_tasks_this_year = list(payload.get("expired_this_year", []))
                self.mainline_rewards = list(payload.get("rewards_this_year", []))
                self.mainline_narrative = list(payload.get("mainline_narrative", []))
                if self._mainline_working is not None:
                    self.current_guidance_text = self._mainline_working.current_guidance_text
            elif event.event_type == SimulationEventType.ACHIEVEMENT_STATE_UPDATE_REQUESTED:
                patch = dict(payload.get("achievement", {}))
                if self._achievement_working is not None and patch:
                    merged = {**self._achievement_working.to_life_state_dict(), **patch}
                    self._achievement_working = AchievementState.from_life_state_dict(merged)
                    self.achievement_changes = merged
                self.newly_unlocked_achievements = list(payload.get("newly_unlocked", []))
                self.achievement_points_gained = int(payload.get("achievement_points_gained", 0))
                self.milestones_this_year = list(payload.get("milestones_this_year", []))
                self.achievement_narrative = list(payload.get("achievement_narrative", []))
            elif event.event_type in {
                SimulationEventType.FAMILY_RELATION_CHANGE_REQUESTED,
                SimulationEventType.FAMILY_STATE_UPDATE_REQUESTED,
                SimulationEventType.RELATIONSHIP_STATUS_CHANGE_REQUESTED,
                SimulationEventType.PARTNER_CREATED,
                SimulationEventType.MARRIAGE_CREATED,
                SimulationEventType.CHILD_CREATED,
                SimulationEventType.FAMILY_PRESSURE_CHANGE_REQUESTED,
                SimulationEventType.PARENT_RELATION_CHANGE_REQUESTED,
                SimulationEventType.PARTNER_RELATION_CHANGE_REQUESTED,
                SimulationEventType.CHILD_RELATION_CHANGE_REQUESTED,
                SimulationEventType.FAMILY_HISTORY_RECORDED,
                SimulationEventType.DIVORCE_CREATED,
            }:
                self._apply_family_event(event.event_type, payload)

    def bind_family_context(self, state: LifeState, rules: dict[str, Any]) -> None:
        self._family_state_age = state.age
        self._family_rules = rules
        if self._family_working is None:
            base = FamilyState.from_life_state_dict(state.family)
            self._family_working = self.family_processor.initialize(base)

    def _apply_family_event(
        self,
        event_type: SimulationEventType,
        payload: dict[str, Any],
    ) -> None:
        if self._family_working is None or self._family_rules is None:
            return
        self._family_working = self.family_processor.process(
            event_type,
            payload,
            self._family_working,
            self._family_state_age,
            self._family_rules,
        )

    def apply_to_state(
        self,
        state: LifeState,
        rules: dict | None = None,
        *,
        advance_age: bool = True,
    ) -> LifeState:
        next_state = state.model_copy(deep=True)
        if advance_age:
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

        if self._family_working is not None:
            next_state.family = self._family_working.to_life_state_dict()

        if self._legal_working is not None:
            next_state.legal = self._legal_working.to_life_state_dict()

        if self._mainline_working is not None:
            next_state.mainline = self._mainline_working.to_life_state_dict()

        if self._achievement_working is not None:
            next_state.achievements = self._achievement_working.to_life_state_dict()

        if self.death_reason is not None:
            next_state.is_dead = True
            next_state.death_reason = self.death_reason

        if self.pending_random_event is not None:
            next_state.pending_random_event = dict(self.pending_random_event)
        if self.pending_legal_event is not None:
            next_state.pending_legal_event = dict(self.pending_legal_event)
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

        from app.modules.mainline.service import MainlineService

        active_mainline_tasks = MainlineService().get_active_task_summaries(
            MainlineState.from_life_state_dict(after.mainline),
            {},
        )

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
            relationship_status_before=self.family_processor.relationship_status_before,
            relationship_status_after=self.family_processor.relationship_status_after,
            partner_relation_delta=self.family_processor.partner_relation_delta,
            parent_child_relation_delta=self.family_processor.parent_child_relation_delta,
            family_pressure_delta=self.family_processor.family_pressure_delta,
            married_this_year=self.family_processor.married_this_year,
            child_born_this_year=self.family_processor.child_born_this_year,
            children_count_delta=self.family_processor.children_count_delta,
            family_history_records=list(self.family_processor.family_history_records),
            family_changes=self.family_processor.summary(),
            pending_legal_event=self.pending_legal_event or after.pending_legal_event,
            legal_changes=dict(self.legal_changes),
            active_mainline_tasks=active_mainline_tasks,
            completed_mainline_tasks_this_year=list(self.completed_mainline_tasks_this_year),
            failed_mainline_tasks_this_year=list(self.failed_mainline_tasks_this_year),
            expired_mainline_tasks_this_year=list(self.expired_mainline_tasks_this_year),
            mainline_rewards=list(self.mainline_rewards),
            mainline_narrative=list(self.mainline_narrative),
            current_guidance_text=self.current_guidance_text or after.mainline.get(
                "current_guidance_text",
                "",
            ),
            mainline_changes=dict(self.mainline_changes),
            narrative_result=self.narrative_result,
            annual_summary_text=(
                self.narrative_result.get("summary_text", "")
                if self.narrative_result
                else "\n".join(self.narrative_lines)
            ),
            major_event_texts=(
                list(self.narrative_result.get("major_event_texts", []))
                if self.narrative_result
                else []
            ),
            display_sections=(
                list(self.narrative_result.get("display_sections", []))
                if self.narrative_result
                else []
            ),
            newly_unlocked_achievements=list(self.newly_unlocked_achievements),
            achievement_points_gained=self.achievement_points_gained,
            milestones_this_year=list(self.milestones_this_year),
            achievement_narrative=list(self.achievement_narrative),
        )

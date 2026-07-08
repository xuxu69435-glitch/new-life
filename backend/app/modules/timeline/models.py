from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.engine.simulation_context import LifeState, YearResult
from app.modules.timeline.constants import SAVE_VERSION, SNAPSHOT_VERSION


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LifeSaveRecord(BaseModel):
    life_id: str
    user_id: str = "local_user"
    local_user_id: str = "local_user"
    rule_version: str
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)
    is_dead: bool = False
    current_age: int = 0
    current_generation: int = 1
    save_version: str = SAVE_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class LifeYearSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    life_id: str
    age_before: int
    age_after: int
    year_index: int
    rule_version: str
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    year_result: dict[str, Any]
    narrative_result: dict[str, Any] | None = None
    triggered_random_events: list[dict[str, Any]] = Field(default_factory=list)
    legal_events: list[dict[str, Any]] = Field(default_factory=list)
    mainline_changes: dict[str, Any] = Field(default_factory=dict)
    achievement_changes: dict[str, Any] = Field(default_factory=dict)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    death_result: dict[str, Any] | None = None
    inheritance_result: dict[str, Any] | None = None
    created_at: str = Field(default_factory=_utc_now)
    snapshot_version: str = SNAPSHOT_VERSION

    @classmethod
    def from_year_advance(
        cls,
        state_before: LifeState,
        state_after: LifeState,
        result: YearResult,
        inheritance_result: dict[str, Any] | None = None,
    ) -> "LifeYearSnapshot":
        death_result = None
        if result.is_dead:
            death_result = {
                "is_dead": True,
                "death_reason": result.death_reason,
                "death_type": result.death_type,
                "age": result.age_after,
            }
        legal_events: list[dict[str, Any]] = []
        if result.legal_changes:
            legal_events.append({"type": "legal_changes", "payload": dict(result.legal_changes)})
        if result.pending_legal_event:
            legal_events.append({"type": "pending_legal_event", "payload": dict(result.pending_legal_event)})

        return cls(
            life_id=result.life_id,
            age_before=result.age_before,
            age_after=result.age_after,
            year_index=result.age_after,
            rule_version=state_after.rule_version,
            state_before=state_before.model_dump(),
            state_after=state_after.model_dump(),
            year_result=result.model_dump(mode="json"),
            narrative_result=dict(result.narrative_result) if result.narrative_result else None,
            triggered_random_events=list(result.triggered_random_events),
            legal_events=legal_events,
            mainline_changes={
                "completed": list(result.completed_mainline_tasks_this_year),
                "failed": list(result.failed_mainline_tasks_this_year),
                "expired": list(result.expired_mainline_tasks_this_year),
                "rewards": list(result.mainline_rewards),
                "changes": dict(result.mainline_changes),
            },
            achievement_changes={
                "newly_unlocked": list(result.newly_unlocked_achievements),
                "points_gained": result.achievement_points_gained,
                "narrative": list(result.achievement_narrative),
            },
            milestones=list(result.milestones_this_year),
            death_result=death_result,
            inheritance_result=dict(inheritance_result) if inheritance_result else result.inheritance_result,
        )


class LifeEventLog(BaseModel):
    event_log_id: str = Field(default_factory=lambda: str(uuid4()))
    life_id: str
    age: int
    event_type: str
    event_category: str
    source_module: str
    source_event_id: str = ""
    title: str
    description: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    created_at: str = Field(default_factory=_utc_now)


class TimelineEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    life_id: str
    age: int
    title: str
    summary: str
    entry_type: str
    category: str
    source_module: str = "timeline"
    source_id: str = ""
    importance: int = 10
    tags: list[str] = Field(default_factory=list)
    display_text: str = ""
    related_snapshot_id: str = ""
    created_at: str = Field(default_factory=_utc_now)

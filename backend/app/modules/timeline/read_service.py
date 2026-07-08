from typing import Any

from app.application.save_migration_service import SaveMigrationService
from app.infrastructure.save.in_memory_repository import InMemorySaveRepository
from app.infrastructure.save.repository import SaveRepository
from app.modules.timeline.models import LifeEventLog, LifeSaveRecord, LifeYearSnapshot, TimelineEntry


class TimelineReadService:
    """Read-only timeline and replay queries. Never recalculates simulation."""

    def __init__(
        self,
        repository: SaveRepository,
        migration: SaveMigrationService | None = None,
    ) -> None:
        self.repository = repository
        self.migration = migration or SaveMigrationService()

    def get_timeline_entries(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        entry_type: str | None = None,
    ) -> list[TimelineEntry]:
        return self.repository.get_timeline_entries(
            life_id,
            age_min=age_min,
            age_max=age_max,
            entry_type=entry_type,
        )

    def get_year_snapshot(self, life_id: str, age: int) -> LifeYearSnapshot | None:
        snapshot = self.repository.get_snapshot_by_age(life_id, age)
        if snapshot is not None:
            return self.migration.ensure_snapshot_shape(snapshot)
        result = self.repository.get_year_result_by_age(life_id, age)
        if result is None:
            return None
        return self.migration.build_snapshot_from_year_result(result)

    def get_year_narrative(self, life_id: str, age: int) -> dict[str, Any] | None:
        snapshot = self.get_year_snapshot(life_id, age)
        if snapshot is None:
            return None
        return {
            "life_id": life_id,
            "age": age,
            "narrative_result": snapshot.narrative_result,
            "annual_summary_text": snapshot.year_result.get("annual_summary_text", ""),
            "narrative_text": snapshot.year_result.get("narrative_text", ""),
            "display_sections": snapshot.year_result.get("display_sections", []),
        }

    def get_year_result_dict(self, life_id: str, age: int) -> dict[str, Any] | None:
        snapshot = self.get_year_snapshot(life_id, age)
        if snapshot is not None:
            return dict(snapshot.year_result)
        result = self.repository.get_year_result_by_age(life_id, age)
        return result.model_dump(mode="json") if result else None

    def get_event_logs(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        event_category: str | None = None,
    ) -> list[LifeEventLog]:
        return self.repository.get_event_logs(
            life_id,
            age_min=age_min,
            age_max=age_max,
            event_category=event_category,
        )

    def get_key_milestones(self, life_id: str) -> list[dict[str, Any]]:
        state = self.repository.get_state(life_id)
        milestones = state.achievements.get("milestones", []) if state.achievements else []
        return list(milestones)

    def get_year_detail(self, life_id: str, age: int) -> dict[str, Any] | None:
        snapshot = self.get_year_snapshot(life_id, age)
        if snapshot is None:
            return None
        entries = [
            entry
            for entry in self.repository.get_timeline_entries(life_id)
            if entry.age == age
        ]
        entries.sort(key=lambda item: -item.importance)
        return {
            "life_id": life_id,
            "age": age,
            "snapshot_id": snapshot.snapshot_id,
            "annual_summary": snapshot.year_result.get("annual_summary_text")
            or snapshot.year_result.get("narrative_text", ""),
            "narrative_result": snapshot.narrative_result,
            "state_changes": {
                "attributes": snapshot.year_result.get("changed_attributes", {}),
                "health": snapshot.year_result.get("changed_health", {}),
                "assets": snapshot.year_result.get("changed_assets", {}),
            },
            "events": [entry.model_dump() for entry in entries],
            "achievements": snapshot.achievement_changes,
            "mainline": snapshot.mainline_changes,
            "milestones": snapshot.milestones,
            "year_result": snapshot.year_result,
        }

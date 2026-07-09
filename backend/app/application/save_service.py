from datetime import datetime, timezone
from typing import Any

from app.application.save_migration_service import SaveMigrationService
from app.engine.simulation_context import LifeState, YearResult
from app.infrastructure.save.in_memory_repository import InMemorySaveRepository
from app.infrastructure.save.repository import SaveRepository
from app.modules.assets.models import AssetState
from app.modules.family.rules import build_default_family_state
from app.modules.legal.rules import build_default_legal_state
from app.modules.achievement.rules import build_default_achievement_state
from app.modules.mainline.rules import build_default_mainline_state
from app.modules.education.rules import build_default_education_state
from app.modules.health.rules import build_default_health_state
from app.modules.career.rules import build_default_career_state
from app.modules.social.rules import build_default_social_state
from app.modules.romance.rules import build_default_romance_state
from app.modules.timeline.generator import EventLogBuilder, TimelineGenerator
from app.modules.timeline.models import LifeSaveRecord, LifeYearSnapshot
from app.modules.timeline.read_service import TimelineReadService


class SaveService:
    def __init__(
        self,
        repository: SaveRepository | None = None,
        migration: SaveMigrationService | None = None,
    ) -> None:
        self.repository = repository or InMemorySaveRepository()
        self.migration = migration or SaveMigrationService()
        self.timeline_reader = TimelineReadService(self.repository, self.migration)
        self._event_log_builder = EventLogBuilder()
        self._timeline_generator = TimelineGenerator()

    def create_life(
        self,
        rule_version: str,
        rules: dict,
        *,
        person_id: str | None = None,
        family: dict | None = None,
        assets: dict | None = None,
        generation: int | None = None,
        age: int = 0,
        source_life_id: str | None = None,
        inheritance_amount: float | None = None,
    ) -> LifeState:
        from uuid import uuid4

        life_id = str(uuid4())
        resolved_person_id = person_id or str(uuid4())
        default_family = build_default_family_state(rules)
        if family is not None:
            family_state = family
        else:
            family_state = default_family.to_life_state_dict()
        if generation is not None:
            family_state["generation"] = generation

        default_assets = AssetState.from_life_state_dict(
            assets or rules.get("default_assets", {}),
            rules,
        ).to_life_state_dict()
        if inheritance_amount is not None:
            default_assets["cash"] = float(default_assets.get("cash", 0.0)) + float(inheritance_amount)
            default_assets["net_worth"] = (
                float(default_assets.get("cash", 0.0))
                + float(default_assets.get("property_value", 0.0))
                - float(default_assets.get("debt", 0.0))
            )

        state = LifeState(
            life_id=life_id,
            person_id=resolved_person_id,
            age=age,
            life_stage="infant",
            attributes=dict(rules.get("default_attributes", {})),
            health=build_default_health_state(rules).to_life_state_dict(),
            family=family_state,
            education=build_default_education_state(rules).to_life_state_dict(),
            career=build_default_career_state(rules).to_life_state_dict(),
            assets=default_assets,
            flags={},
            legal=build_default_legal_state(rules).to_life_state_dict(),
            mainline=build_default_mainline_state(rules).to_life_state_dict(),
            achievements=build_default_achievement_state(rules).to_life_state_dict(),
            social=build_default_social_state(rules).to_life_state_dict(),
            romance=build_default_romance_state(rules).to_life_state_dict(),
            rule_version=rule_version,
        )
        if source_life_id is not None:
            state.flags["source_life_id"] = source_life_id
        if inheritance_amount is not None:
            state.flags["inheritance_amount"] = inheritance_amount

        record = LifeSaveRecord(
            life_id=life_id,
            rule_version=rule_version,
            current_age=age,
            current_generation=int(family_state.get("generation", 1)),
            metadata={"source_life_id": source_life_id} if source_life_id else {},
        )
        self.repository.save_record(record)
        self.save_life_state(state, rules=rules)
        return state

    def save_life_state(self, state: LifeState, *, rules: dict | None = None) -> None:
        migrated = self.migration.ensure_life_state_shape(state, rules)
        self.repository.save_state(migrated)
        record = self.migration.ensure_save_record_shape(
            self.repository.get_record(migrated.life_id),
            migrated,
        )
        self.repository.save_record(record)

    def get_life_state(self, life_id: str, *, rules: dict | None = None) -> LifeState:
        state = self.repository.get_state(life_id)
        return self.migration.ensure_life_state_shape(state, rules)

    def find_by_person_id(self, person_id: str, *, rules: dict | None = None) -> LifeState | None:
        for record in self.repository.list_records():
            try:
                state = self.repository.get_state(record.life_id)
            except KeyError:
                continue
            if state.person_id == person_id:
                return self.migration.ensure_life_state_shape(state, rules)
        return None

    def append_timeline(self, result: YearResult) -> None:
        self.repository.append_year_result(result)

    def persist_year_record(
        self,
        state_before: LifeState,
        state_after: LifeState,
        result: YearResult,
        inheritance_result: dict[str, Any] | None = None,
    ) -> LifeYearSnapshot:
        snapshot = LifeYearSnapshot.from_year_advance(
            state_before,
            state_after,
            result,
            inheritance_result=inheritance_result,
        )
        snapshot = self.migration.ensure_snapshot_shape(snapshot)
        event_logs = self._event_log_builder.build(result, snapshot.snapshot_id)
        timeline_entries = self._timeline_generator.generate(result, snapshot)

        persist_bundle = getattr(self.repository, "persist_year_bundle", None)
        if callable(persist_bundle):
            persist_bundle(
                snapshot=snapshot,
                year_result=result,
                event_logs=event_logs,
                timeline_entries=timeline_entries,
            )
        else:
            self.append_timeline(result)
            self.repository.append_snapshot(snapshot)
            self.repository.append_event_logs(result.life_id, event_logs)
            self.repository.append_timeline_entries(result.life_id, timeline_entries)
        return snapshot

    def get_timeline(self, life_id: str) -> list[YearResult]:
        return self.repository.get_year_results(life_id)

    def list_saves(self) -> list[LifeSaveRecord]:
        return self.repository.list_records()

    def get_save_record(self, life_id: str) -> LifeSaveRecord | None:
        record = self.repository.get_record(life_id)
        if record is None and self.repository.state_exists(life_id):
            state = self.get_life_state(life_id)
            return self.migration.ensure_save_record_shape(None, state)
        return record

    def get_timeline_entries(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        entry_type: str | None = None,
    ):
        return self.timeline_reader.get_timeline_entries(
            life_id,
            age_min=age_min,
            age_max=age_max,
            entry_type=entry_type,
        )

    def get_year_snapshot(self, life_id: str, age: int) -> LifeYearSnapshot | None:
        return self.timeline_reader.get_year_snapshot(life_id, age)

    def get_year_detail(self, life_id: str, age: int) -> dict[str, Any] | None:
        return self.timeline_reader.get_year_detail(life_id, age)

    def get_year_narrative(self, life_id: str, age: int) -> dict[str, Any] | None:
        return self.timeline_reader.get_year_narrative(life_id, age)

    def get_year_result_by_age(self, life_id: str, age: int) -> dict[str, Any] | None:
        return self.timeline_reader.get_year_result_dict(life_id, age)

    def get_key_milestones(self, life_id: str) -> list[dict[str, Any]]:
        return self.timeline_reader.get_key_milestones(life_id)

    def get_event_logs(
        self,
        life_id: str,
        *,
        age_min: int | None = None,
        age_max: int | None = None,
        event_category: str | None = None,
    ):
        return self.timeline_reader.get_event_logs(
            life_id,
            age_min=age_min,
            age_max=age_max,
            event_category=event_category,
        )

    def save_inheritance(self, life_id: str, result: dict) -> None:
        self.repository.save_inheritance(life_id, result)

    def get_inheritance(self, life_id: str) -> dict:
        return self.repository.get_inheritance(life_id)

    def save_heir_continuation(self, source_life_id: str, record: dict) -> None:
        self.repository.save_heir_continuation(source_life_id, record)

    def get_heir_continuation(self, source_life_id: str) -> dict | None:
        return self.repository.get_heir_continuation(source_life_id)

    def migrate_legacy_state_dict(self, data: dict[str, Any], rules: dict | None = None) -> dict[str, Any]:
        return self.migration.migrate_legacy_state_dict(data, rules)

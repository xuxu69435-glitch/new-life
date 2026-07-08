from datetime import datetime, timezone
from typing import Any

from app.engine.simulation_context import LifeState, SimulationEvent, YearResult
from app.modules.achievement.rules import build_default_achievement_state
from app.modules.legal.rules import build_default_legal_state
from app.modules.mainline.rules import build_default_mainline_state
from app.modules.timeline.constants import SAVE_VERSION, SNAPSHOT_VERSION
from app.modules.timeline.models import LifeSaveRecord, LifeYearSnapshot


class SaveMigrationService:
    def ensure_life_state_shape(self, state: LifeState, rules: dict[str, Any] | None = None) -> LifeState:
        data = state.model_dump()
        rules = rules or {}
        if not data.get("legal"):
            data["legal"] = build_default_legal_state(rules).to_life_state_dict()
        if not data.get("mainline"):
            data["mainline"] = build_default_mainline_state(rules).to_life_state_dict()
        if not data.get("achievements"):
            data["achievements"] = build_default_achievement_state(rules).to_life_state_dict()
        if data.get("flags") is None:
            data["flags"] = {}
        return LifeState.model_validate(data)

    def ensure_save_record_shape(self, record: LifeSaveRecord | None, state: LifeState) -> LifeSaveRecord:
        generation = int(state.family.get("generation", 1)) if isinstance(state.family, dict) else 1
        if record is None:
            return LifeSaveRecord(
                life_id=state.life_id,
                rule_version=state.rule_version,
                is_dead=state.is_dead,
                current_age=state.age,
                current_generation=generation,
                save_version=SAVE_VERSION,
            )
        return record.model_copy(
            update={
                "rule_version": state.rule_version,
                "is_dead": state.is_dead,
                "current_age": state.age,
                "current_generation": generation,
                "save_version": record.save_version or SAVE_VERSION,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def ensure_snapshot_shape(self, snapshot: LifeYearSnapshot) -> LifeYearSnapshot:
        data = snapshot.model_dump()
        data.setdefault("snapshot_version", SNAPSHOT_VERSION)
        data.setdefault("narrative_result", None)
        data.setdefault("triggered_random_events", [])
        data.setdefault("legal_events", [])
        data.setdefault("mainline_changes", {})
        data.setdefault("achievement_changes", {})
        data.setdefault("milestones", [])
        data.setdefault("death_result", None)
        data.setdefault("inheritance_result", None)
        return LifeYearSnapshot.model_validate(data)

    def build_snapshot_from_year_result(
        self,
        result: YearResult,
        *,
        state_before: dict[str, Any] | None = None,
        state_after: dict[str, Any] | None = None,
    ) -> LifeYearSnapshot:
        before = state_before or {"life_id": result.life_id, "age": result.age_before}
        after = state_after or {"life_id": result.life_id, "age": result.age_after}
        snapshot = LifeYearSnapshot.from_year_advance(
            LifeState.model_validate(self._minimal_state(before, result.life_id, result.age_before)),
            LifeState.model_validate(self._minimal_state(after, result.life_id, result.age_after)),
            result,
            inheritance_result=result.inheritance_result,
        )
        return self.ensure_snapshot_shape(snapshot)

    def _minimal_state(self, partial: dict[str, Any], life_id: str, age: int) -> dict[str, Any]:
        base = {
            "life_id": life_id,
            "person_id": partial.get("person_id", life_id),
            "age": age,
            "life_stage": partial.get("life_stage", "infant"),
            "is_dead": partial.get("is_dead", False),
            "attributes": partial.get("attributes", {}),
            "health": partial.get("health", {}),
            "family": partial.get("family", {}),
            "education": partial.get("education", {}),
            "career": partial.get("career", {}),
            "assets": partial.get("assets", {}),
            "flags": partial.get("flags", {}),
            "legal": partial.get("legal", {}),
            "mainline": partial.get("mainline", {}),
            "achievements": partial.get("achievements", {}),
            "rule_version": partial.get("rule_version", "v1"),
        }
        base.update(partial)
        return base

    def migrate_legacy_state_dict(self, data: dict[str, Any], rules: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self.ensure_life_state_shape(LifeState.model_validate(data), rules)
        return state.model_dump()

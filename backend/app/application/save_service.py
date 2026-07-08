from uuid import uuid4

from app.engine.simulation_context import LifeState, YearResult
from app.modules.assets.models import AssetState
from app.modules.family.rules import build_default_family_state
from app.modules.legal.rules import build_default_legal_state
from app.modules.achievement.rules import build_default_achievement_state
from app.modules.mainline.rules import build_default_mainline_state
from app.modules.education.rules import build_default_education_state
from app.modules.career.rules import build_default_career_state
from app.modules.health.rules import build_default_health_state


class SaveService:
    def __init__(self) -> None:
        self._states: dict[str, LifeState] = {}
        self._timeline: dict[str, list[YearResult]] = {}
        self._inheritance: dict[str, dict] = {}
        self._heir_continuations: dict[str, dict] = {}

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
            rule_version=rule_version,
        )
        if source_life_id is not None:
            state.flags["source_life_id"] = source_life_id
        if inheritance_amount is not None:
            state.flags["inheritance_amount"] = inheritance_amount
        self.save_life_state(state)
        self._timeline[state.life_id] = []
        return state

    def save_life_state(self, state: LifeState) -> None:
        self._states[state.life_id] = state

    def get_life_state(self, life_id: str) -> LifeState:
        return self._states[life_id]

    def find_by_person_id(self, person_id: str) -> LifeState | None:
        for state in self._states.values():
            if state.person_id == person_id:
                return state
        return None

    def append_timeline(self, result: YearResult) -> None:
        self._timeline.setdefault(result.life_id, []).append(result)

    def get_timeline(self, life_id: str) -> list[YearResult]:
        return list(self._timeline.get(life_id, []))

    def save_inheritance(self, life_id: str, result: dict) -> None:
        self._inheritance[life_id] = result

    def get_inheritance(self, life_id: str) -> dict:
        return self._inheritance.get(life_id, {"status": "not_available"})

    def save_heir_continuation(self, source_life_id: str, record: dict) -> None:
        self._heir_continuations[source_life_id] = record

    def get_heir_continuation(self, source_life_id: str) -> dict | None:
        return self._heir_continuations.get(source_life_id)

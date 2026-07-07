from uuid import uuid4

from app.engine.simulation_context import LifeState, YearResult
from app.modules.health.rules import build_default_health_state


class SaveService:
    def __init__(self) -> None:
        self._states: dict[str, LifeState] = {}
        self._timeline: dict[str, list[YearResult]] = {}
        self._inheritance: dict[str, dict] = {}

    def create_life(self, rule_version: str, rules: dict) -> LifeState:
        life_id = str(uuid4())
        person_id = str(uuid4())
        state = LifeState(
            life_id=life_id,
            person_id=person_id,
            age=0,
            life_stage="infant",
            attributes=dict(rules.get("default_attributes", {})),
            health=build_default_health_state(rules).to_life_state_dict(),
            family={"relations": []},
            education={"track": rules.get("education", {}).get("default_track", "not_started")},
            career={"title": "none", "income": 0.0},
            assets=dict(rules.get("default_assets", {})),
            flags={},
            rule_version=rule_version,
        )
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

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.event_bus import EventBus
from app.engine.result_collector import ResultCollector
from app.engine.simulation_context import LifeState, SimulationContext
from app.infrastructure.rng import ServerRandom
from app.modules.career.rules import build_default_career_state
from app.modules.education.rules import build_default_education_state
from app.modules.family.rules import build_default_family_state
from app.rules.rule_loader import RuleLoader


@pytest.fixture
def rules() -> dict:
    return RuleLoader().load("v1")


@pytest.fixture
def life_state(rules: dict) -> LifeState:
    return LifeState(
        life_id="life-1",
        person_id="person-1",
        age=0,
        life_stage="infant",
        attributes=dict(rules["default_attributes"]),
        health=dict(rules["default_health"]),
        family=build_default_family_state(rules).to_life_state_dict(),
        education=build_default_education_state(rules).to_life_state_dict(),
        career=build_default_career_state(rules).to_life_state_dict(),
        assets=dict(rules["default_assets"]),
        rule_version=rules["version"],
    )


def make_context(
    state: LifeState,
    rules: dict,
    choices: dict | None = None,
    seed: int = 1,
) -> SimulationContext:
    return SimulationContext(
        state=state,
        player_choices=choices or {"annual_focus": "balanced_year"},
        rule_version=state.rule_version,
        rng=ServerRandom(seed),
        event_bus=EventBus(),
        result_collector=ResultCollector(),
        rules=rules,
    )

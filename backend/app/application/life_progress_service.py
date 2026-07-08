from typing import Any

from app.engine.simulation_context import YearResult
from app.engine.simulation_engine import SimulationEngine
from app.rules.rule_loader import RuleLoader
from app.application.save_service import SaveService


class LifeProgressService:
    def __init__(
        self,
        save_service: SaveService,
        rule_loader: RuleLoader,
        engine: SimulationEngine,
    ) -> None:
        self.save_service = save_service
        self.rule_loader = rule_loader
        self.engine = engine

    def advance_one_year(self, life_id: str, player_choices: dict[str, Any]) -> YearResult:
        state = self.save_service.get_life_state(life_id)
        rules = self.rule_loader.load(state.rule_version)
        next_state, result, inheritance_result = self.engine.advance_one_year(
            state,
            player_choices,
            rules,
        )
        self.save_service.save_life_state(next_state, rules=rules)
        self.save_service.persist_year_record(
            state,
            next_state,
            result,
            inheritance_result=inheritance_result,
        )
        if inheritance_result is not None:
            self.save_service.save_inheritance(life_id, inheritance_result)
        return result

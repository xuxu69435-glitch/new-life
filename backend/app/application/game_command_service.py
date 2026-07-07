from typing import Any

from app.application.life_progress_service import LifeProgressService
from app.application.save_service import SaveService
from app.engine.simulation_context import LifeState, YearResult
from app.engine.simulation_engine import SimulationEngine
from app.rules.rule_loader import RuleLoader


class GameCommandService:
    def __init__(
        self,
        save_service: SaveService | None = None,
        rule_loader: RuleLoader | None = None,
        engine: SimulationEngine | None = None,
    ) -> None:
        self.save_service = save_service or SaveService()
        self.rule_loader = rule_loader or RuleLoader()
        self.engine = engine or SimulationEngine()
        self.life_progress = LifeProgressService(
            self.save_service,
            self.rule_loader,
            self.engine,
        )

    def create_life(self, rule_version: str | None = None) -> tuple[LifeState, list[dict[str, Any]]]:
        resolved_version = rule_version or self.rule_loader.version_manager.get_version_for_new_life()
        rules = self.rule_loader.load(resolved_version)
        state = self.save_service.create_life(resolved_version, rules)
        choices = self.engine.get_available_choices(state, rules)
        return state, choices

    def get_life_state(self, life_id: str) -> tuple[LifeState, list[dict[str, Any]]]:
        state = self.save_service.get_life_state(life_id)
        rules = self.rule_loader.load(state.rule_version)
        choices = [] if state.is_dead else self.engine.get_available_choices(state, rules)
        return state, choices

    def advance_one_year(self, life_id: str, player_choices: dict[str, Any]) -> YearResult:
        return self.life_progress.advance_one_year(life_id, player_choices)

    def get_timeline(self, life_id: str) -> list[YearResult]:
        return self.save_service.get_timeline(life_id)

    def get_family_tree(self, life_id: str) -> dict[str, Any]:
        state = self.save_service.get_life_state(life_id)
        return {"life_id": life_id, "family": state.family, "status": "placeholder"}

    def get_inheritance_result(self, life_id: str) -> dict[str, Any]:
        return self.save_service.get_inheritance(life_id)

    def get_person(self, person_id: str) -> LifeState | None:
        return self.save_service.find_by_person_id(person_id)


game_service = GameCommandService()

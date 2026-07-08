from typing import Any

from app.application.life_progress_service import LifeProgressService
from app.application.save_service import SaveService
from app.engine.simulation_context import LifeState, YearResult
from app.engine.simulation_engine import SimulationEngine
from app.infrastructure.errors import DomainError
from app.modules.family.models import FamilyState
from app.rules.rule_loader import RuleLoader


class HeirContinuationError(DomainError):
    """Raised when heir continuation cannot be performed."""


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
        choices = [] if state.is_dead else self.get_available_choices(state, rules)
        return state, choices

    def get_available_choices(self, state: LifeState, rules: dict) -> list[dict[str, Any]]:
        return self.engine.get_available_choices(state, rules)

    def advance_one_year(self, life_id: str, player_choices: dict[str, Any]) -> YearResult:
        return self.life_progress.advance_one_year(life_id, player_choices)

    def get_pending_random_event(self, life_id: str) -> dict[str, Any] | None:
        state = self.save_service.get_life_state(life_id)
        return state.pending_random_event

    def submit_random_event_choice(self, life_id: str, choice_id: str) -> dict[str, Any]:
        state = self.save_service.get_life_state(life_id)
        rules = self.rule_loader.load(state.rule_version)
        next_state, choice_result = self.engine.submit_random_event_choice(
            state,
            choice_id,
            rules,
        )
        self.save_service.save_life_state(next_state)
        return {
            "life_id": life_id,
            "choice_result": choice_result,
            "pending_random_event": next_state.pending_random_event,
            "state": next_state,
        }

    def get_timeline(self, life_id: str) -> list[YearResult]:
        return self.save_service.get_timeline(life_id)

    def get_family_tree(self, life_id: str) -> dict[str, Any]:
        state = self.save_service.get_life_state(life_id)
        return {"life_id": life_id, "family": state.family}

    def get_inheritance_result(self, life_id: str) -> dict[str, Any]:
        return self.save_service.get_inheritance(life_id)

    def get_playable_heirs(self, life_id: str) -> dict[str, Any]:
        state = self.save_service.get_life_state(life_id)
        if not state.is_dead:
            return {"life_id": life_id, "playable_heirs": [], "status": "life_not_ended"}

        inheritance = self.save_service.get_inheritance(life_id)
        if inheritance.get("status") == "not_available":
            return {"life_id": life_id, "playable_heirs": [], "status": "inheritance_not_available"}

        rules = self.rule_loader.load(state.rule_version)
        inheritance_rules = rules.get("inheritance", {})
        if not inheritance_rules.get("continue_as_heir_enabled", False):
            return {"life_id": life_id, "playable_heirs": [], "status": "continue_as_heir_disabled"}

        family = FamilyState.from_life_state_dict(state.family)
        distribution = inheritance.get("distribution", {})
        playable_heirs: list[dict[str, Any]] = []
        for child in family.playable_children():
            amount = float(distribution.get(child.person_id, 0.0))
            playable_heirs.append(
                {
                    "person_id": child.person_id,
                    "name": child.name,
                    "relation": child.relation,
                    "inheritance_amount": amount,
                    "generation": family.generation + 1,
                    "start_age": int(
                        inheritance_rules.get("continue_as_heir", {}).get("start_age", 0)
                    ),
                }
            )

        return {
            "life_id": life_id,
            "source_life_id": life_id,
            "playable_heirs": playable_heirs,
            "status": "available" if playable_heirs else "no_playable_heirs",
        }

    def continue_as_heir(self, life_id: str, heir_person_id: str) -> dict[str, Any]:
        state = self.save_service.get_life_state(life_id)
        if not state.is_dead:
            raise HeirContinuationError("Cannot continue as heir before death is confirmed.")

        heirs_payload = self.get_playable_heirs(life_id)
        heir = next(
            (item for item in heirs_payload["playable_heirs"] if item["person_id"] == heir_person_id),
            None,
        )
        if heir is None:
            raise HeirContinuationError(f"Heir is not playable: {heir_person_id}")

        rules = self.rule_loader.load(state.rule_version)
        inheritance_rules = rules.get("inheritance", {})
        continue_rules = inheritance_rules.get("continue_as_heir", {})
        start_age = int(continue_rules.get("start_age", 0))
        inherit_cash = bool(continue_rules.get("inherit_cash_to_new_life", True))
        inheritance_amount = float(heir["inheritance_amount"]) if inherit_cash else 0.0

        family = FamilyState.from_life_state_dict(state.family)
        new_family = {
            "parents": [
                {
                    "person_id": state.person_id,
                    "name": "Deceased parent",
                    "relation": "parent",
                    "playable": False,
                }
            ],
            "spouse": None,
            "children": [],
            "generation": heir["generation"],
            "family_tree_id": family.family_tree_id,
        }

        new_state = self.save_service.create_life(
            state.rule_version,
            rules,
            person_id=heir_person_id,
            family=new_family,
            generation=heir["generation"],
            age=start_age,
            source_life_id=life_id,
            inheritance_amount=inheritance_amount,
        )

        record = {
            "source_life_id": life_id,
            "heir_person_id": heir_person_id,
            "new_life_id": new_state.life_id,
            "inheritance_amount": inheritance_amount,
            "generation": heir["generation"],
            "start_age": start_age,
            "status": "continued",
        }
        self.save_service.save_heir_continuation(life_id, record)
        choices = self.engine.get_available_choices(new_state, rules)
        return {
            **record,
            "state": new_state,
            "available_choices": choices,
        }

    def get_person(self, person_id: str) -> LifeState | None:
        return self.save_service.find_by_person_id(person_id)


game_service = GameCommandService()

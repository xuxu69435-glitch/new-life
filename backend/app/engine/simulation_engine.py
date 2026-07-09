from typing import Any

from app.engine.event_bus import EventBus
from app.engine.module_runner import SimulationModule
from app.engine.result_collector import ResultCollector
from app.engine.simulation_context import LifeState, SimulationContext, YearResult
from app.infrastructure.errors import InvalidPlayerChoiceError, LifeAlreadyEndedError, PendingLegalEventError, PendingRandomEventError
from app.infrastructure.rng import ServerRandom
from app.modules.assets.service import AssetsService
from app.modules.attributes.service import AttributesService
from app.modules.career.service import CareerService
from app.modules.death.service import DeathService
from app.modules.education.service import EducationService
from app.modules.family.service import FamilyService
from app.modules.health.service import HealthService
from app.modules.inheritance.service import InheritanceService
from app.modules.legal.service import LegalService
from app.modules.life_stage.service import LifeStageService
from app.modules.mainline.service import MainlineService
from app.modules.achievement.service import AchievementService
from app.modules.narrative.service import NarrativeService
from app.modules.random_events.service import RandomEventsService
from app.modules.romance.service import RomanceService
from app.modules.social.service import SocialService


class SimulationEngine:
    def __init__(self, rng_seed: int | None = None) -> None:
        self.rng_seed = rng_seed
        self.annual_modules: list[SimulationModule] = [
            LifeStageService(),
            AttributesService(),
            EducationService(),
            CareerService(),
            FamilyService(),
            SocialService(),
            RomanceService(),
            AssetsService(),
            HealthService(),
            RandomEventsService(),
            LegalService(),
            DeathService(),
            MainlineService(),
        ]
        self.inheritance_module = InheritanceService()
        self.narrative_module = NarrativeService()
        self.achievement_module = AchievementService()

    def advance_one_year(
        self,
        current_state: LifeState,
        player_choices: dict[str, Any],
        rules: dict,
    ) -> tuple[LifeState, YearResult, dict[str, Any] | None]:
        if current_state.is_dead:
            raise LifeAlreadyEndedError("Cannot advance a dead life.")
        if current_state.pending_legal_event is not None:
            raise PendingLegalEventError(
                "Cannot advance year until the pending legal event choice is submitted."
            )
        if current_state.pending_random_event is not None:
            raise PendingRandomEventError(
                "Cannot advance year until the pending random event choice is submitted."
            )

        choices = dict(player_choices or {})
        choices.setdefault("annual_focus", "balanced_year")
        self._validate_choices(current_state, choices, rules)

        context = SimulationContext(
            state=current_state,
            player_choices=choices,
            rule_version=current_state.rule_version,
            rng=ServerRandom(self.rng_seed),
            event_bus=EventBus(),
            result_collector=ResultCollector(),
            rules=rules,
        )
        context.result_collector.bind_family_context(current_state, rules)
        context.result_collector.bind_legal_context(current_state)
        context.result_collector.bind_mainline_context(current_state)
        context.result_collector.bind_achievement_context(current_state)
        context.result_collector.bind_social_context(current_state)
        context.result_collector.bind_romance_context(current_state)

        for module in self.annual_modules:
            module.run(context)
            context.result_collector.collect_from_events(context.event_bus.all())

        if context.result_collector.death_confirmed:
            self.inheritance_module.run(context)

        self.narrative_module.run(context)
        context.result_collector.collect_from_events(context.event_bus.all())

        self.achievement_module.run(context)
        context.result_collector.collect_from_events(context.event_bus.all())

        next_state = context.result_collector.apply_to_state(current_state, rules)
        next_choices = [] if next_state.is_dead else self.get_available_choices(next_state, rules)
        result = context.result_collector.to_year_result(
            before=current_state,
            after=next_state,
            occurred_events=context.event_bus.all(),
            next_available_choices=next_choices,
        )
        return next_state, result, context.result_collector.inheritance_result

    def submit_random_event_choice(
        self,
        current_state: LifeState,
        choice_id: str,
        rules: dict,
    ) -> tuple[LifeState, dict[str, Any]]:
        if current_state.is_dead:
            raise LifeAlreadyEndedError("Cannot resolve choices for a dead life.")
        if current_state.pending_random_event is None:
            raise InvalidPlayerChoiceError("No pending random event is available.")

        context = SimulationContext(
            state=current_state,
            player_choices={"annual_focus": "balanced_year"},
            rule_version=current_state.rule_version,
            rng=ServerRandom(self.rng_seed),
            event_bus=EventBus(),
            result_collector=ResultCollector(),
            rules=rules,
        )

        context.result_collector.bind_family_context(current_state, rules)
        context.result_collector.bind_legal_context(current_state)
        context.result_collector.bind_mainline_context(current_state)
        context.result_collector.bind_achievement_context(current_state)
        context.result_collector.bind_social_context(current_state)
        context.result_collector.bind_romance_context(current_state)

        random_events_module = RandomEventsService()
        choice_result = random_events_module.submit_choice(context, choice_id)
        context.result_collector.collect_from_events(context.event_bus.all())

        death_module = DeathService()
        death_module.run(context)
        context.result_collector.collect_from_events(context.event_bus.all())

        if context.result_collector.death_confirmed:
            self.inheritance_module.run(context)
            context.result_collector.collect_from_events(context.event_bus.all())

        next_state = context.result_collector.apply_to_state(
            current_state,
            rules,
            advance_age=False,
        )
        next_state.pending_random_event = None
        return next_state, choice_result

    def submit_legal_choice(
        self,
        current_state: LifeState,
        choice_id: str,
        rules: dict,
    ) -> tuple[LifeState, dict[str, Any]]:
        if current_state.is_dead:
            raise LifeAlreadyEndedError("Cannot resolve choices for a dead life.")
        if current_state.pending_legal_event is None:
            raise InvalidPlayerChoiceError("No pending legal event is available.")

        context = SimulationContext(
            state=current_state,
            player_choices={"annual_focus": "balanced_year"},
            rule_version=current_state.rule_version,
            rng=ServerRandom(self.rng_seed),
            event_bus=EventBus(),
            result_collector=ResultCollector(),
            rules=rules,
        )
        context.result_collector.bind_family_context(current_state, rules)
        context.result_collector.bind_legal_context(current_state)
        context.result_collector.bind_mainline_context(current_state)
        context.result_collector.bind_achievement_context(current_state)
        context.result_collector.bind_social_context(current_state)
        context.result_collector.bind_romance_context(current_state)

        legal_module = LegalService()
        choice_result = legal_module.submit_choice(context, choice_id)
        context.result_collector.collect_from_events(context.event_bus.all())

        next_state = context.result_collector.apply_to_state(
            current_state,
            rules,
            advance_age=False,
        )
        next_state.pending_legal_event = None
        return next_state, choice_result

    def get_available_choices(self, state: LifeState, rules: dict) -> list[dict[str, Any]]:
        choices = rules.get("available_choices", {})
        return list(choices.get(state.life_stage, choices.get("default", [])))

    def _validate_choices(self, state: LifeState, choices: dict[str, Any], rules: dict) -> None:
        available = {choice["id"] for choice in self.get_available_choices(state, rules)}
        annual_focus = choices.get("annual_focus")
        if annual_focus not in available:
            raise InvalidPlayerChoiceError(f"Choice is not available: {annual_focus}")

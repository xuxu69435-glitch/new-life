from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.random_events.choice_effect_resolver import RandomEventChoiceEffectResolver
from app.modules.random_events.draw_state import blocked_social_sub_categories, build_draw_state
from app.modules.random_events.effect_resolver import RandomEventEffectResolver
from app.modules.random_events.library_models import PendingRandomEvent, V1EventDefinition
from app.modules.random_events.models import RandomEventDefinition
from app.modules.random_events.rules import eligible_event_pool
from app.modules.random_events.v1_draw import RandomEventV1DrawService
from app.modules.legal.models import LegalState
from app.modules.legal.rules import blocks_normal_random_events
from app.rules.random_event_library_loader import RandomEventLibraryLoader
from app.rules.social_event_library_loader import SocialEventLibraryLoader


class RandomEventsService:
    name = "random_events"
    can_confirm_death = False

    def __init__(
        self,
        effect_resolver: RandomEventEffectResolver | None = None,
        choice_effect_resolver: RandomEventChoiceEffectResolver | None = None,
        library_loader: RandomEventLibraryLoader | None = None,
        social_library_loader: SocialEventLibraryLoader | None = None,
        draw_service: RandomEventV1DrawService | None = None,
    ) -> None:
        self.effect_resolver = effect_resolver or RandomEventEffectResolver()
        self.choice_effect_resolver = choice_effect_resolver or RandomEventChoiceEffectResolver(
            self.effect_resolver
        )
        self.library_loader = library_loader or RandomEventLibraryLoader()
        self.social_library_loader = social_library_loader or SocialEventLibraryLoader()
        self.draw_service = draw_service or RandomEventV1DrawService()

    def run(self, context: SimulationContext) -> None:
        if context.state.pending_random_event is not None:
            return
        if context.state.is_dead:
            return

        legal = LegalState.from_life_state_dict(context.state.legal)
        if blocks_normal_random_events(legal):
            return

        random_rules = context.rules.get("random_events", {})
        if random_rules.get("use_v1_library", False):
            self._run_v1_library(context, random_rules)
            return

        for event_def in eligible_event_pool(context.state.life_stage, context.rules):
            if not self._should_trigger_legacy(event_def, context):
                continue

            context.event_bus.publish(
                SimulationEventType.RANDOM_EVENT_TRIGGERED,
                self.name,
                event_def.to_event_payload(),
            )
            self._apply_legacy_effects(event_def, context)

    def submit_choice(
        self,
        context: SimulationContext,
        choice_id: str,
    ) -> dict[str, Any]:
        pending = context.state.pending_random_event
        if pending is None:
            raise ValueError("No pending random event to resolve.")

        event = self._find_event(str(pending["event_id"]))
        if event is None:
            raise ValueError(f"Unknown pending event: {pending['event_id']}")

        choice = next(
            (item for item in event.choices if item.choice_id == choice_id),
            None,
        )
        if choice is None:
            raise ValueError(f"Choice is not available: {choice_id}")

        context.event_bus.publish(
            SimulationEventType.RANDOM_EVENT_TRIGGERED,
            self.name,
            {
                **event.to_pending_payload(),
                "resolved_choice_id": choice.choice_id,
            },
        )
        for event_type, payload in self.choice_effect_resolver.resolve_choice(
            event,
            choice,
            context,
        ):
            context.event_bus.publish(event_type, self.name, payload)

        context.event_bus.publish(
            SimulationEventType.RANDOM_EVENT_CHOICE_APPLIED,
            self.name,
            {
                "event_id": event.event_id,
                "choice_id": choice.choice_id,
                "choice_text": choice.choice_text,
                "effects_text": choice.effects_text,
            },
        )
        self._record_event_history(context, event)
        context.result_collector.pending_random_event = None
        return {
            "event_id": event.event_id,
            "choice_id": choice.choice_id,
            "choice_text": choice.choice_text,
            "effects_text": choice.effects_text,
        }

    def _find_event(self, event_id: str) -> V1EventDefinition | None:
        if event_id.startswith("S"):
            return self.social_library_loader.load().by_id().get(event_id)
        return self.library_loader.load().by_id().get(event_id)

    def _run_v1_library(self, context: SimulationContext, random_rules: dict) -> None:
        draw_state = build_draw_state(context)
        if draw_state.is_dead:
            return

        library = self.library_loader.load()
        event_history = self._event_history(context)
        death_limit = float(random_rules.get("direct_death_probability_limit", 0.03))
        legal = LegalState.from_life_state_dict(draw_state.legal)

        death_pool = self.draw_service.eligible_direct_death_events(
            library.events,
            draw_state,
            event_history,
        )
        if death_pool and self.draw_service.should_enter_direct_death_pool(
            death_limit,
            context.rng,
        ):
            death_event = self.draw_service.draw_by_weight(death_pool, context.rng)
            if death_event is not None:
                self._resolve_system_event(death_event, context)
                return

        normal_pool = self.draw_service.eligible_normal_events(
            library.events,
            draw_state,
            event_history,
        )
        social_pool: list[V1EventDefinition] = []
        if random_rules.get("use_social_library", False):
            social_library = self.social_library_loader.load()
            social_pool = self.draw_service.eligible_social_events(
                social_library.events,
                draw_state,
                event_history,
                blocked_sub_categories=blocked_social_sub_categories(legal),
            )

        combined_pool = normal_pool + social_pool
        selected = self.draw_service.draw_by_weight(combined_pool, context.rng)
        if selected is None:
            return

        if selected.pool_type == "direct_death":
            self._resolve_system_event(selected, context)
            return

        pending = PendingRandomEvent(
            event_id=selected.event_id,
            name=selected.name,
            category=selected.category,
            event_text=selected.event_text,
            choices=selected.to_pending_payload()["choices"],
            year_age=context.state.age,
            pool_type=selected.pool_type,
        )
        context.result_collector.pending_random_event = pending.model_dump()
        context.event_bus.publish(
            SimulationEventType.RANDOM_EVENT_TRIGGERED,
            self.name,
            {
                **selected.to_pending_payload(),
                "status": "pending_choice",
            },
        )

    def _resolve_system_event(
        self,
        event: V1EventDefinition,
        context: SimulationContext,
    ) -> None:
        system_choice = next(
            (choice for choice in event.choices if choice.is_system_choice),
            event.choices[0],
        )
        context.event_bus.publish(
            SimulationEventType.RANDOM_EVENT_TRIGGERED,
            self.name,
            event.to_pending_payload(),
        )
        for event_type, payload in self.choice_effect_resolver.resolve_choice(
            event,
            system_choice,
            context,
        ):
            context.event_bus.publish(event_type, self.name, payload)
        self._record_event_history(context, event)

    def _apply_legacy_effects(
        self,
        event_def: RandomEventDefinition,
        context: SimulationContext,
    ) -> None:
        for event_type, payload in self.effect_resolver.resolve(event_def, context):
            context.event_bus.publish(event_type, self.name, payload)

    def _should_trigger_legacy(
        self,
        event_def: RandomEventDefinition,
        context: SimulationContext,
    ) -> bool:
        probability = float(event_def.probability)
        if probability <= 0:
            return False
        return context.rng.random() <= probability

    def _event_history(self, context: SimulationContext) -> dict[str, Any]:
        history = context.state.flags.get("random_event_history", {})
        if isinstance(history, dict):
            return history
        return {}

    def _record_event_history(
        self,
        context: SimulationContext,
        event: V1EventDefinition,
    ) -> None:
        history = dict(self._event_history(context))
        history[event.event_id] = {"last_age": context.state.age}
        context.result_collector.changed_flags["random_event_history"] = history

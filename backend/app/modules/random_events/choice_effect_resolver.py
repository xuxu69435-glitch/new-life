from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.infrastructure.errors import RandomEventEffectError
from app.modules.random_events.effect_resolver import RandomEventEffectResolver
from app.modules.random_events.library_models import V1EventChoice, V1EventDefinition


class RandomEventChoiceEffectResolver:
    def __init__(self, effect_resolver: RandomEventEffectResolver | None = None) -> None:
        self.effect_resolver = effect_resolver or RandomEventEffectResolver()

    def resolve_choice(
        self,
        event: V1EventDefinition,
        choice: V1EventChoice,
        context: SimulationContext,
    ) -> list[tuple[SimulationEventType, dict[str, Any]]]:
        resolved: list[tuple[SimulationEventType, dict[str, Any]]] = []
        for raw_effect in choice.effects:
            effect_type = str(raw_effect.get("type", "")).strip()
            if effect_type == "unsupported_effect":
                resolved.append(
                    (
                        SimulationEventType.UNSUPPORTED_EFFECT_RECORDED,
                        {
                            "event_id": event.event_id,
                            "choice_id": choice.choice_id,
                            "target": raw_effect.get("target", ""),
                            "reason": raw_effect.get("reason", ""),
                            "effects_text": choice.effects_text,
                        },
                    )
                )
                continue

            pseudo_event = self._as_legacy_event(event, choice, raw_effect)
            resolved.extend(self.effect_resolver.resolve(pseudo_event, context))
        return resolved

    def _as_legacy_event(
        self,
        event: V1EventDefinition,
        choice: V1EventChoice,
        raw_effect: dict[str, Any],
    ):
        from app.modules.random_events.models import RandomEventDefinition

        effect_type = str(raw_effect.get("type", "")).strip()
        if effect_type not in RandomEventEffectResolver.ALLOWED_EFFECT_TYPES:
            raise RandomEventEffectError(
                f"Unknown choice effect type '{effect_type}' for event '{event.event_id}'."
            )

        return RandomEventDefinition(
            id=event.event_id,
            name=event.name,
            category=event.category,
            stage="any",
            probability=0.0,
            direct_death=effect_type == "direct_death_candidate",
            effects=[raw_effect],
            narrative_text=choice.effects_text,
            death_reason=str(raw_effect.get("reason") or event.name),
        )

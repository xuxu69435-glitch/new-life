from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.infrastructure.errors import RandomEventEffectError
from app.modules.random_events.models import RandomEventDefinition, RandomEventEffect


class RandomEventEffectResolver:
    ALLOWED_EFFECT_TYPES = {
        "attribute_change",
        "health_change",
        "asset_change",
        "direct_death_candidate",
        "narrative_tag",
        "flag_set",
    }

    def resolve(
        self,
        event_def: RandomEventDefinition,
        context: SimulationContext,
    ) -> list[tuple[SimulationEventType, dict[str, Any]]]:
        resolved: list[tuple[SimulationEventType, dict[str, Any]]] = []
        for raw_effect in event_def.effects:
            effect = RandomEventEffect.model_validate(self._with_event_source(raw_effect, event_def))
            resolved.append(self._resolve_effect(effect, event_def, context))
        return resolved

    def _with_event_source(
        self,
        raw_effect: dict[str, Any],
        event_def: RandomEventDefinition,
    ) -> dict[str, Any]:
        payload = dict(raw_effect)
        payload.setdefault("source_event_id", event_def.id)
        payload.setdefault("source_event_name", event_def.display_name())
        return payload

    def _resolve_effect(
        self,
        effect: RandomEventEffect,
        event_def: RandomEventDefinition,
        context: SimulationContext,
    ) -> tuple[SimulationEventType, dict[str, Any]]:
        effect_type = effect.type.strip()
        if effect_type not in self.ALLOWED_EFFECT_TYPES:
            raise RandomEventEffectError(
                f"Unknown random event effect type: {effect_type} "
                f"for event '{event_def.id}'."
            )

        metadata = {
            "source_event_id": effect.source_event_id or event_def.id,
            "source_event_name": effect.source_event_name or event_def.display_name(),
            "reason": effect.reason,
        }

        if effect_type == "attribute_change":
            return SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED, {
                "key": effect.target,
                "delta": int(effect.value),
                **metadata,
            }

        if effect_type == "health_change":
            target = effect.target or "health_score"
            return SimulationEventType.HEALTH_CHANGE_REQUESTED, {
                "key": target,
                "delta": int(effect.value),
                **metadata,
            }

        if effect_type == "asset_change":
            return SimulationEventType.ASSET_CHANGE_REQUESTED, {
                "key": effect.target,
                "delta": float(effect.value),
                **metadata,
            }

        if effect_type == "direct_death_candidate":
            death_reason = str(effect.reason or event_def.death_reason or event_def.display_name())
            return SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED, {
                "reason": death_reason,
                "death_type": "direct_death",
                "probability": 1.0,
                "event_id": event_def.id,
                "category": event_def.category,
                **metadata,
            }

        if effect_type == "narrative_tag":
            return SimulationEventType.NARRATIVE_REQUESTED, {
                "tag": str(effect.target or effect.value),
                "text": str(effect.reason or effect.value),
                **metadata,
            }

        if effect_type == "flag_set":
            return SimulationEventType.FLAG_SET_REQUESTED, {
                "key": effect.target,
                "value": effect.value,
                **metadata,
            }

        raise RandomEventEffectError(
            f"Unsupported random event effect type: {effect_type} for event '{event_def.id}'."
        )

from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType


class MainlineRewardResolver:
    ALLOWED_REWARD_TYPES = {
        "attribute_change",
        "health_change",
        "asset_change",
        "family_relation_change",
        "flag_set",
        "mainline_flag_set",
        "narrative_tag",
    }

    def apply_rewards(
        self,
        context: SimulationContext,
        rewards: list[dict[str, Any]],
        task_id: str,
    ) -> list[dict[str, Any]]:
        applied: list[dict[str, Any]] = []
        for reward in rewards:
            reward_type = str(reward.get("type", ""))
            if reward_type not in self.ALLOWED_REWARD_TYPES:
                raise ValueError(f"Unsupported mainline reward type: {reward_type}")
            if reward_type == "attribute_change":
                context.event_bus.publish(
                    SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED,
                    "mainline",
                    {
                        "key": reward["key"],
                        "delta": int(reward.get("delta", 0)),
                        "reason": f"mainline:{task_id}",
                    },
                )
            elif reward_type == "health_change":
                context.event_bus.publish(
                    SimulationEventType.HEALTH_CHANGE_REQUESTED,
                    "mainline",
                    {
                        "key": reward["key"],
                        "delta": int(reward.get("delta", 0)),
                        "reason": f"mainline:{task_id}",
                    },
                )
            elif reward_type == "asset_change":
                context.event_bus.publish(
                    SimulationEventType.ASSET_CHANGE_REQUESTED,
                    "mainline",
                    {
                        "key": reward["key"],
                        "delta": float(reward.get("delta", 0.0)),
                        "reason": f"mainline:{task_id}",
                    },
                )
            elif reward_type == "family_relation_change":
                context.event_bus.publish(
                    SimulationEventType.FAMILY_RELATION_CHANGE_REQUESTED,
                    "mainline",
                    {
                        "key": reward.get("key", reward.get("target", "partner_relation")),
                        "delta": int(reward.get("delta", 0)),
                        "reason": f"mainline:{task_id}",
                    },
                )
            elif reward_type == "flag_set":
                context.event_bus.publish(
                    SimulationEventType.FLAG_SET_REQUESTED,
                    "mainline",
                    {"key": reward["key"], "value": reward.get("value", True)},
                )
            elif reward_type == "mainline_flag_set":
                context.event_bus.publish(
                    SimulationEventType.MAINLINE_STATE_UPDATE_REQUESTED,
                    "mainline",
                    {
                        "mainline_flags_patch": {reward["key"]: reward.get("value", True)},
                        "reason": f"mainline_reward:{task_id}",
                    },
                )
            elif reward_type == "narrative_tag":
                context.event_bus.publish(
                    SimulationEventType.NARRATIVE_REQUESTED,
                    "mainline",
                    {"text": str(reward.get("text", ""))},
                )
            applied.append(dict(reward))
        return applied

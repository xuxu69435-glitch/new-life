from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType


class AchievementRewardResolver:
    ALLOWED_REWARD_TYPES = {
        "achievement_points",
        "attribute_change",
        "health_change",
        "asset_change",
        "flag_set",
        "narrative_tag",
    }

    def apply_rewards(
        self,
        context: SimulationContext,
        rewards: list[dict[str, Any]],
        achievement_id: str,
        default_points: int,
    ) -> dict[str, Any]:
        summary = {"achievement_points": default_points, "rewards": []}
        for reward in rewards:
            reward_type = str(reward.get("type", "achievement_points"))
            if reward_type not in self.ALLOWED_REWARD_TYPES:
                raise ValueError(f"Unsupported achievement reward type: {reward_type}")
            if reward_type == "achievement_points":
                summary["achievement_points"] += int(reward.get("points", 0))
            elif reward_type == "attribute_change":
                context.event_bus.publish(
                    SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED,
                    "achievement",
                    {
                        "key": reward["key"],
                        "delta": int(reward.get("delta", 0)),
                        "reason": f"achievement:{achievement_id}",
                    },
                )
            elif reward_type == "health_change":
                context.event_bus.publish(
                    SimulationEventType.HEALTH_CHANGE_REQUESTED,
                    "achievement",
                    {
                        "key": reward["key"],
                        "delta": int(reward.get("delta", 0)),
                        "reason": f"achievement:{achievement_id}",
                    },
                )
            elif reward_type == "asset_change":
                context.event_bus.publish(
                    SimulationEventType.ASSET_CHANGE_REQUESTED,
                    "achievement",
                    {
                        "key": reward["key"],
                        "delta": float(reward.get("delta", 0.0)),
                        "reason": f"achievement:{achievement_id}",
                    },
                )
            elif reward_type == "flag_set":
                context.event_bus.publish(
                    SimulationEventType.FLAG_SET_REQUESTED,
                    "achievement",
                    {"key": reward["key"], "value": reward.get("value", True)},
                )
            elif reward_type == "narrative_tag":
                context.event_bus.publish(
                    SimulationEventType.NARRATIVE_REQUESTED,
                    "achievement",
                    {"text": str(reward.get("text", ""))},
                )
            summary["rewards"].append(dict(reward))
        return summary

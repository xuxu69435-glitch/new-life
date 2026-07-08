from app.infrastructure.errors import RuleValidationError
from app.modules.achievement.condition_evaluator import AchievementConditionEvaluator
from app.modules.achievement.library_models import AchievementLibraryV1
from app.modules.achievement.reward_resolver import AchievementRewardResolver


class AchievementValidator:
    ALLOWED_CATEGORIES = {
        "growth",
        "education",
        "career",
        "family",
        "health",
        "wealth",
        "legal",
        "legacy",
        "mainline",
        "special",
    }
    ALLOWED_TIERS = {"bronze", "silver", "gold", "legendary"}
    ALLOWED_STATUSES = {"active", "partial", "planned"}

    def validate_library(self, library: AchievementLibraryV1) -> None:
        seen: set[str] = set()
        evaluator = AchievementConditionEvaluator()
        for item in library.achievements:
            if not item.achievement_id.strip():
                raise RuleValidationError("achievement_id cannot be empty.")
            if item.achievement_id in seen:
                raise RuleValidationError(f"Duplicate achievement_id: {item.achievement_id}")
            seen.add(item.achievement_id)
            if not item.title.strip():
                raise RuleValidationError(f"Achievement {item.achievement_id} title cannot be empty.")
            if not item.description.strip():
                raise RuleValidationError(
                    f"Achievement {item.achievement_id} description cannot be empty."
                )
            if item.category not in self.ALLOWED_CATEGORIES:
                raise RuleValidationError(
                    f"Achievement {item.achievement_id} has invalid category: {item.category}"
                )
            if item.tier not in self.ALLOWED_TIERS:
                raise RuleValidationError(
                    f"Achievement {item.achievement_id} has invalid tier: {item.tier}"
                )
            if item.points < 0:
                raise RuleValidationError(
                    f"Achievement {item.achievement_id} points cannot be negative."
                )
            if not item.unlock_conditions and not item.trigger_conditions:
                raise RuleValidationError(
                    f"Achievement {item.achievement_id} must define unlock or trigger conditions."
                )
            if not isinstance(item.rewards, list):
                raise RuleValidationError(f"Achievement {item.achievement_id} rewards must be a list.")
            if item.implementation_status not in self.ALLOWED_STATUSES:
                raise RuleValidationError(
                    f"Achievement {item.achievement_id} has invalid implementation_status."
                )
            conditions = item.unlock_conditions or item.trigger_conditions
            self._validate_conditions(item.achievement_id, conditions, evaluator)
            for reward in item.rewards:
                reward_type = str(reward.get("type", "achievement_points"))
                if reward_type not in AchievementRewardResolver.ALLOWED_REWARD_TYPES:
                    raise RuleValidationError(
                        f"Achievement {item.achievement_id} has invalid reward type: {reward_type}"
                    )

    def _validate_conditions(
        self,
        achievement_id: str,
        conditions: dict,
        evaluator: AchievementConditionEvaluator,
    ) -> None:
        for key in conditions:
            if key not in evaluator.SUPPORTED_KEYS:
                raise RuleValidationError(
                    f"Achievement {achievement_id} uses unsupported condition key: {key}"
                )

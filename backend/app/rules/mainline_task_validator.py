from app.infrastructure.errors import RuleValidationError
from app.modules.mainline.condition_evaluator import MainlineConditionEvaluator
from app.modules.mainline.library_models import MainlineTaskLibraryV1
from app.modules.mainline.reward_resolver import MainlineRewardResolver
from app.rules.mainline_task_library_loader import MainlineTaskLibraryLoader


class MainlineTaskValidator:
    ALLOWED_STATUSES = {"active", "partial", "planned"}

    def validate_library(self, library: MainlineTaskLibraryV1) -> None:
        seen_ids: set[str] = set()
        for task in library.tasks:
            if not task.task_id.strip():
                raise RuleValidationError("Mainline task_id cannot be empty.")
            if task.task_id in seen_ids:
                raise RuleValidationError(f"Duplicate mainline task_id: {task.task_id}")
            seen_ids.add(task.task_id)
            if not task.title.strip():
                raise RuleValidationError(f"Mainline task {task.task_id} title cannot be empty.")
            if not task.description.strip():
                raise RuleValidationError(
                    f"Mainline task {task.task_id} description cannot be empty."
                )
            if not task.life_stages and task.min_age > task.max_age:
                raise RuleValidationError(
                    f"Mainline task {task.task_id} min_age cannot exceed max_age."
                )
            if task.min_age > task.max_age:
                raise RuleValidationError(
                    f"Mainline task {task.task_id} min_age cannot exceed max_age."
                )
            if not task.life_stages and task.min_age == 0 and task.max_age == 0:
                raise RuleValidationError(
                    f"Mainline task {task.task_id} must define life_stages or age range."
                )
            if not task.completion_conditions:
                raise RuleValidationError(
                    f"Mainline task {task.task_id} completion_conditions cannot be empty."
                )
            if not isinstance(task.rewards, list):
                raise RuleValidationError(f"Mainline task {task.task_id} rewards must be a list.")
            if task.implementation_status not in self.ALLOWED_STATUSES:
                raise RuleValidationError(
                    f"Mainline task {task.task_id} has invalid implementation_status."
                )
            self._validate_conditions(task.task_id, task.activation_conditions)
            self._validate_conditions(task.task_id, task.completion_conditions)
            self._validate_conditions(task.task_id, task.failure_conditions)
            self._validate_conditions(task.task_id, task.expiration_conditions)
            for reward in task.rewards:
                reward_type = str(reward.get("type", ""))
                if reward_type not in MainlineRewardResolver.ALLOWED_REWARD_TYPES:
                    raise RuleValidationError(
                        f"Mainline task {task.task_id} has invalid reward type: {reward_type}"
                    )

    def _validate_conditions(self, task_id: str, conditions: dict) -> None:
        if not conditions:
            return
        evaluator = MainlineConditionEvaluator()
        for key in conditions:
            if key not in evaluator.SUPPORTED_KEYS:
                raise RuleValidationError(
                    f"Mainline task {task_id} uses unsupported condition key: {key}"
                )
            if key == "or_conditions":
                groups = conditions["or_conditions"]
                if not isinstance(groups, list):
                    raise RuleValidationError(
                        f"Mainline task {task_id} or_conditions must be a list."
                    )
                for group in groups:
                    self._validate_conditions(task_id, group)

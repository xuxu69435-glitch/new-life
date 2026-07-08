from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.achievement.condition_evaluator import AchievementConditionEvaluator
from app.modules.achievement.library_models import AchievementDefinition
from app.modules.achievement.milestone_tracker import MilestoneTracker
from app.modules.achievement.models import AchievementState
from app.modules.achievement.reward_resolver import AchievementRewardResolver
from app.modules.achievement.rules import get_achievement_rules
from app.modules.family.models import FamilyState
from app.modules.legal.models import LegalState
from app.rules.achievement_library_loader import AchievementLibraryLoader


class AchievementService:
    name = "achievement"
    can_confirm_death = False

    def __init__(self, library_loader: AchievementLibraryLoader | None = None) -> None:
        self.library_loader = library_loader or AchievementLibraryLoader()
        self.condition_evaluator = AchievementConditionEvaluator()
        self.reward_resolver = AchievementRewardResolver()
        self.milestone_tracker = MilestoneTracker()

    def run(self, context: SimulationContext) -> None:
        rules = get_achievement_rules(context.rules)
        if not rules.get("use_achievement_v1", False):
            return

        achievement = self._working(context)
        before_state = context.state
        after_state = context.result_collector.snapshot_state(context.state, context.rules)

        achievement.newly_unlocked_this_year = []
        self._update_tracking_flags(before_state, after_state, achievement)

        milestones = self.milestone_tracker.detect(
            before_state,
            after_state,
            achievement,
            inheritance_result=context.result_collector.inheritance_result,
            married_this_year=context.result_collector.family_processor.married_this_year,
            child_born_this_year=context.result_collector.family_processor.child_born_this_year,
        )
        achievement.milestones.extend(milestones)

        narrative_tags = self._narrative_tags(context)
        newly_unlocked: list[dict[str, Any]] = []
        points_gained = 0
        narrative_lines: list[str] = []

        library = self.library_loader.load()
        for definition in library.active_achievements():
            if self._is_unlocked(definition, achievement) and not definition.repeatable:
                continue
            conditions = definition.unlock_conditions or definition.trigger_conditions
            if not self.condition_evaluator.matches(
                conditions,
                after_state,
                achievement,
                narrative_tags=narrative_tags,
                inheritance_result=context.result_collector.inheritance_result,
            ):
                continue
            unlocked_payload = self._unlock(
                context,
                achievement,
                definition,
                after_state.age,
            )
            newly_unlocked.append(unlocked_payload)
            points_gained += int(unlocked_payload.get("points_gained", 0))
            if definition.narrative_text:
                narrative_lines.append(definition.narrative_text)

        context.event_bus.publish(
            SimulationEventType.ACHIEVEMENT_STATE_UPDATE_REQUESTED,
            self.name,
            {
                "achievement": achievement.to_life_state_dict(),
                "newly_unlocked": newly_unlocked,
                "milestones_this_year": milestones,
                "achievement_points_gained": points_gained,
                "achievement_narrative": narrative_lines,
                "reason": "annual_achievement_tick",
            },
        )

    def unlock_heir_continuation_for_life(self, state: Any, rules: dict) -> Any:
        from app.engine.simulation_context import LifeState

        achievement = AchievementState.from_life_state_dict(state.achievements)
        achievement.achievement_flags["heir_continuation_unlocked"] = True
        library = self.library_loader.load()
        definition = library.by_id().get("A030")
        if definition and "A030" not in achievement.unlocked_achievements:
            achievement.unlocked_achievements.append("A030")
            achievement.achievement_points += definition.points
            achievement.achievement_history.append(
                {
                    "achievement_id": "A030",
                    "title": definition.title,
                    "description": definition.description,
                    "age": state.age,
                    "year": state.age,
                    "source": "heir_continuation",
                }
            )
            achievement.last_achievement_change = "unlocked:A030"
            achievement.milestones.append(
                {
                    "milestone_id": "heir_continuation",
                    "title": "继续后代人生",
                    "age": state.age,
                    "year": state.age,
                    "source": "heir_continuation",
                    "description": "后代继续了你的人生。",
                }
            )
        if isinstance(state, LifeState):
            return state.model_copy(update={"achievements": achievement.to_life_state_dict()})
        state.achievements = achievement.to_life_state_dict()
        return state

    def get_public_achievements(
        self,
        achievement_state: AchievementState,
        rules: dict,
    ) -> list[dict[str, Any]]:
        library = self.library_loader.load()
        results: list[dict[str, Any]] = []
        for definition in library.achievements:
            if definition.implementation_status == "planned":
                continue
            unlocked = definition.achievement_id in achievement_state.unlocked_achievements
            if definition.hidden and not unlocked:
                results.append(
                    {
                        "achievement_id": definition.achievement_id,
                        "title": "未发现",
                        "description": "隐藏成就",
                        "category": definition.category,
                        "tier": definition.tier,
                        "hidden": True,
                        "unlocked": False,
                    }
                )
            else:
                results.append(
                    {
                        "achievement_id": definition.achievement_id,
                        "title": definition.title,
                        "description": definition.description,
                        "category": definition.category,
                        "tier": definition.tier,
                        "points": definition.points,
                        "hidden": definition.hidden,
                        "unlocked": unlocked,
                    }
                )
        return results

    def _unlock(
        self,
        context: SimulationContext,
        achievement: AchievementState,
        definition: AchievementDefinition,
        age: int,
    ) -> dict[str, Any]:
        if definition.achievement_id not in achievement.unlocked_achievements:
            achievement.unlocked_achievements.append(definition.achievement_id)
        achievement.newly_unlocked_this_year.append(definition.achievement_id)
        reward_summary = self.reward_resolver.apply_rewards(
            context,
            definition.rewards,
            definition.achievement_id,
            definition.points,
        )
        total_points = int(reward_summary["achievement_points"])
        achievement.achievement_points += total_points
        achievement.achievement_history.append(
            {
                "achievement_id": definition.achievement_id,
                "title": definition.title,
                "description": definition.description,
                "age": age,
                "year": age,
                "source": "achievement",
            }
        )
        achievement.last_achievement_change = f"unlocked:{definition.achievement_id}"
        return {
            "achievement_id": definition.achievement_id,
            "title": definition.title,
            "description": definition.description,
            "points_gained": total_points,
            "narrative_text": definition.narrative_text,
        }

    def _is_unlocked(self, definition: AchievementDefinition, achievement: AchievementState) -> bool:
        return definition.achievement_id in achievement.unlocked_achievements

    def _update_tracking_flags(
        self,
        before: Any,
        after: Any,
        achievement: AchievementState,
    ) -> None:
        family = FamilyState.from_life_state_dict(after.family)
        legal = LegalState.from_life_state_dict(after.legal)
        legal_before = LegalState.from_life_state_dict(before.legal)
        flags = achievement.achievement_flags
        if family.relationship_status in {"dating", "married"}:
            flags["ever_dating"] = True
        if family.relationship_status == "married":
            flags["ever_married"] = True
        if family.children_count > 0:
            flags["ever_children"] = True
        if legal.is_in_prison or legal.has_criminal_record:
            flags["ever_in_prison"] = True
        if legal_before.is_in_prison and not legal.is_in_prison and not legal.is_fugitive:
            flags["ever_released"] = True

    def _narrative_tags(self, context: SimulationContext) -> list[str]:
        narrative = context.result_collector.narrative_result or {}
        return list(narrative.get("tags", []))

    def _working(self, context: SimulationContext) -> AchievementState:
        if context.result_collector._achievement_working is None:
            context.result_collector.bind_achievement_context(context.state)
        return context.result_collector._achievement_working

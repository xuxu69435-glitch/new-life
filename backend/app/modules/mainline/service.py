from typing import Any

from app.engine.simulation_context import LifeState, SimulationContext, SimulationEventType
from app.modules.education.models import EducationState
from app.modules.legal.models import LegalState
from app.modules.mainline.condition_evaluator import MainlineConditionEvaluator
from app.modules.mainline.library_models import MainlineTask
from app.modules.mainline.models import MainlineState
from app.modules.mainline.reward_resolver import MainlineRewardResolver
from app.modules.mainline.rules import get_mainline_rules, is_legal_special_chapter
from app.rules.mainline_task_library_loader import MainlineTaskLibraryLoader


class MainlineService:
    name = "mainline"
    can_confirm_death = False

    NORMAL_CATEGORIES = {"normal", "growth", "family", "career", "education", "elder"}

    def __init__(self, library_loader: MainlineTaskLibraryLoader | None = None) -> None:
        self.library_loader = library_loader or MainlineTaskLibraryLoader()
        self.condition_evaluator = MainlineConditionEvaluator()
        self.reward_resolver = MainlineRewardResolver()

    def run(self, context: SimulationContext) -> None:
        mainline_rules = get_mainline_rules(context.rules)
        if not mainline_rules.get("use_mainline_v1", False):
            return

        mainline = self._working(context)
        eval_state = context.result_collector.snapshot_state(context.state, context.rules)
        legal = LegalState.from_life_state_dict(eval_state.legal)

        completed_this_year: list[str] = []
        failed_this_year: list[str] = []
        expired_this_year: list[str] = []
        rewards_this_year: list[dict[str, Any]] = []
        narrative_lines: list[str] = []

        if eval_state.is_dead:
            expired_this_year.extend(
                task_id for task_id in mainline.active_tasks if task_id not in mainline.expired_tasks
            )
            mainline.active_tasks = []
            mainline.current_guidance_text = "人生已结束，主线任务停止更新。"
            self._record_chapter(mainline, "deceased", eval_state.age)
            self._publish_year_summary(
                context,
                mainline,
                completed_this_year,
                failed_this_year,
                expired_this_year,
                rewards_this_year,
                narrative_lines,
            )
            return

        chapter = self._resolve_chapter(eval_state, legal)
        if chapter != mainline.current_chapter:
            self._record_chapter(mainline, chapter, eval_state.age)
        mainline.current_chapter = chapter
        mainline.current_stage = eval_state.life_stage

        if legal.is_fugitive:
            mainline.current_guidance_text = "潜逃中，主线任务暂停。"
            self._publish_year_summary(
                context,
                mainline,
                completed_this_year,
                failed_this_year,
                expired_this_year,
                rewards_this_year,
                narrative_lines,
            )
            return

        library = self.library_loader.load()
        tasks_by_id = library.by_id()

        self._update_college_progress(mainline, eval_state)

        if legal.is_in_prison:
            self._deactivate_normal_tasks(mainline, tasks_by_id)

        for task in sorted(library.active_tasks(), key=lambda item: item.priority):
            if not self._can_activate(task, mainline, eval_state, legal):
                continue
            if task.task_id not in mainline.active_tasks:
                mainline.active_tasks.append(task.task_id)
                mainline.task_progress.setdefault(task.task_id, {"status": "active"})
                mainline.last_mainline_change = f"activated:{task.task_id}"

        active_copy = list(mainline.active_tasks)
        for task_id in active_copy:
            task = tasks_by_id.get(task_id)
            if task is None:
                continue

            if task.can_expire and eval_state.age > task.max_age:
                if self.condition_evaluator.matches(
                    task.expiration_conditions or {"age_min": task.max_age + 1},
                    eval_state,
                    mainline,
                ) or eval_state.age > task.max_age:
                    self._expire_task(mainline, task_id)
                    expired_this_year.append(task_id)
                    continue

            if task.failure_conditions and self.condition_evaluator.matches(
                task.failure_conditions,
                eval_state,
                mainline,
            ):
                self._fail_task(mainline, task, failed_this_year, narrative_lines)
                continue

            if self.condition_evaluator.matches(task.completion_conditions, eval_state, mainline):
                applied = self.reward_resolver.apply_rewards(context, task.rewards, task.task_id)
                rewards_this_year.extend(applied)
                self._complete_task(mainline, task, completed_this_year, narrative_lines)

        mainline.current_guidance_text = self._build_guidance(mainline, tasks_by_id, legal)
        self._publish_year_summary(
            context,
            mainline,
            completed_this_year,
            failed_this_year,
            expired_this_year,
            rewards_this_year,
            narrative_lines,
        )

    def _can_activate(
        self,
        task: MainlineTask,
        mainline: MainlineState,
        state: LifeState,
        legal: LegalState,
    ) -> bool:
        if task.implementation_status != "active":
            return False
        if not task.repeatable:
            if task.task_id in mainline.completed_tasks:
                return False
            if task.task_id in mainline.failed_tasks:
                return False
            if task.task_id in mainline.expired_tasks:
                return False
        if task.task_id in mainline.active_tasks:
            return False
        if state.age < task.min_age or state.age > task.max_age:
            return False
        if task.life_stages:
            stage = {"child": "childhood"}.get(state.life_stage, state.life_stage)
            if stage not in task.life_stages:
                return False

        if legal.is_in_prison:
            if task.task_category not in {"prison", "legal"} and not task.activation_conditions.get(
                "is_in_prison"
            ):
                return False
        elif legal.is_under_supervision:
            if task.task_category in {"career", "family"} and task.task_id in {
                "M011",
                "M012",
                "M017",
            }:
                return False
        else:
            if task.task_category in {"prison"}:
                return False

        if not self.condition_evaluator.matches(task.activation_conditions, state, mainline):
            return False
        return True

    def _deactivate_normal_tasks(
        self,
        mainline: MainlineState,
        tasks_by_id: dict[str, MainlineTask],
    ) -> None:
        kept: list[str] = []
        for task_id in mainline.active_tasks:
            task = tasks_by_id.get(task_id)
            if task and (task.task_category in {"prison", "legal"} or is_legal_special_chapter(task.chapter)):
                kept.append(task_id)
        mainline.active_tasks = kept

    def _update_college_progress(self, mainline: MainlineState, state: LifeState) -> None:
        education = EducationState.from_life_state_dict(state.education, {})
        if education.current_stage != "college":
            return
        progress = mainline.task_progress.setdefault("M009", {"status": "active", "college_years": 0})
        progress["college_years"] = int(progress.get("college_years", 0)) + 1

    def _complete_task(
        self,
        mainline: MainlineState,
        task: MainlineTask,
        completed_this_year: list[str],
        narrative_lines: list[str],
    ) -> None:
        if task.task_id in mainline.active_tasks:
            mainline.active_tasks.remove(task.task_id)
        if task.task_id not in mainline.completed_tasks:
            mainline.completed_tasks.append(task.task_id)
        mainline.task_progress[task.task_id] = {"status": "completed"}
        mainline.last_mainline_change = f"completed:{task.task_id}"
        completed_this_year.append(task.task_id)
        if task.on_complete_text:
            narrative_lines.append(task.on_complete_text)
            mainline.active_mainline_event = {
                "task_id": task.task_id,
                "title": task.title,
                "text": task.on_complete_text,
                "type": "completed",
            }

    def _fail_task(
        self,
        mainline: MainlineState,
        task: MainlineTask,
        failed_this_year: list[str],
        narrative_lines: list[str],
    ) -> None:
        if task.task_id in mainline.active_tasks:
            mainline.active_tasks.remove(task.task_id)
        if task.task_id not in mainline.failed_tasks:
            mainline.failed_tasks.append(task.task_id)
        mainline.task_progress[task.task_id] = {"status": "failed"}
        mainline.last_mainline_change = f"failed:{task.task_id}"
        failed_this_year.append(task.task_id)
        if task.on_failed_text:
            narrative_lines.append(task.on_failed_text)

    def _expire_task(self, mainline: MainlineState, task_id: str) -> None:
        if task_id in mainline.active_tasks:
            mainline.active_tasks.remove(task_id)
        if task_id not in mainline.expired_tasks:
            mainline.expired_tasks.append(task_id)
        mainline.task_progress[task_id] = {"status": "expired"}
        mainline.last_mainline_change = f"expired:{task_id}"

    def _resolve_chapter(self, state: LifeState, legal: LegalState) -> str:
        if legal.is_fugitive:
            return "fugitive"
        if legal.is_in_prison:
            return "prison"
        if legal.has_criminal_record and not legal.is_in_prison:
            return "legal_recovery"
        age = state.age
        if age <= 2:
            return "infant"
        if age <= 6:
            return "toddler"
        if age <= 12:
            return "primary"
        if age <= 15:
            return "middle"
        if age <= 17:
            return "high"
        if age <= 22 and str(state.education.get("current_stage", "")) == "college":
            return "college"
        if age <= 35:
            return "young_adult"
        if age <= 59:
            return "midlife"
        return "elder"

    def _build_guidance(
        self,
        mainline: MainlineState,
        tasks_by_id: dict[str, MainlineTask],
        legal: LegalState,
    ) -> str:
        if legal.is_in_prison:
            return "服刑期间，专注于改造与出狱目标。"
        if not mainline.active_tasks:
            return "当前阶段暂无新的主线目标，继续过好每一年。"
        first = tasks_by_id.get(mainline.active_tasks[0])
        if first:
            return f"当前目标：{first.title}。{first.description}"
        return "继续推进当前人生阶段目标。"

    def _record_chapter(self, mainline: MainlineState, chapter: str, age: int) -> None:
        mainline.chapter_history.append({"chapter": chapter, "age": age})

    def _publish_year_summary(
        self,
        context: SimulationContext,
        mainline: MainlineState,
        completed: list[str],
        failed: list[str],
        expired: list[str],
        rewards: list[dict[str, Any]],
        narrative_lines: list[str],
    ) -> None:
        for line in narrative_lines:
            context.event_bus.publish(
                SimulationEventType.NARRATIVE_REQUESTED,
                self.name,
                {"text": line},
            )
        context.event_bus.publish(
            SimulationEventType.MAINLINE_STATE_UPDATE_REQUESTED,
            self.name,
            {
                "mainline": mainline.to_life_state_dict(),
                "completed_this_year": completed,
                "failed_this_year": failed,
                "expired_this_year": expired,
                "rewards_this_year": rewards,
                "mainline_narrative": narrative_lines,
                "reason": "annual_mainline_tick",
            },
        )

    def _working(self, context: SimulationContext) -> MainlineState:
        if context.result_collector._mainline_working is None:
            context.result_collector.bind_mainline_context(context.state)
        return context.result_collector._mainline_working

    def get_active_task_summaries(
        self,
        mainline: MainlineState,
        rules: dict,
    ) -> list[dict[str, Any]]:
        library = self.library_loader.load()
        tasks_by_id = library.by_id()
        summaries: list[dict[str, Any]] = []
        for task_id in mainline.active_tasks:
            task = tasks_by_id.get(task_id)
            if not task:
                continue
            summaries.append(
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "description": task.description,
                    "chapter": task.chapter,
                    "completion_summary": self._summarize_conditions(task.completion_conditions),
                    "progress": mainline.task_progress.get(task.task_id, {}),
                }
            )
        return summaries

    def _summarize_conditions(self, conditions: dict[str, Any]) -> str:
        if not conditions:
            return "无特殊条件"
        parts: list[str] = []
        for key, value in conditions.items():
            parts.append(f"{key}={value}")
        return "，".join(parts[:4])

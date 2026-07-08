import math
from typing import Any

from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.legal.models import LegalState
from app.modules.legal.rules import get_legal_rules
from app.rules.legal_event_library_loader import LegalEventLibraryLoader


class LegalService:
    name = "legal"
    can_confirm_death = False

    def __init__(self, library_loader: LegalEventLibraryLoader | None = None) -> None:
        self.library_loader = library_loader or LegalEventLibraryLoader()

    def run(self, context: SimulationContext) -> None:
        legal = self._working(context)
        legal_rules = get_legal_rules(context.rules)

        if legal.is_under_supervision and legal.supervision_remaining_years > 0:
            legal.supervision_remaining_years = max(0, legal.supervision_remaining_years - 1)
            if legal.supervision_remaining_years <= 0:
                legal.is_under_supervision = False
                legal.normal_job_locked = False
                legal.career_locked = False
                legal.last_legal_event = "E092"
                self._record_history(legal, "E092", {"status": "supervision_ended"})

        if legal.has_criminal_record and not legal.is_in_prison and not legal.is_fugitive:
            if legal.years_after_release >= 0 and legal.release_age is not None:
                legal.years_after_release += 1
                if legal.post_release_employment_penalty_year < 6:
                    legal.post_release_employment_penalty_year += 1
            if legal.research_job_ban_remaining_years > 0:
                legal.research_job_ban_remaining_years = max(
                    0, legal.research_job_ban_remaining_years - 1
                )

        if legal.is_fugitive:
            legal.fugitive_years += 1
            self._set_pending(context, "E089")
        elif legal.is_in_prison and legal.sentence_remaining_years > 0:
            self._set_pending(context, "E082")
        else:
            context.result_collector.pending_legal_event = None

        self._publish_update(context, legal, "annual_legal_tick")

    def begin_sentencing(
        self,
        context: SimulationContext,
        sentence_years: int,
    ) -> dict[str, Any]:
        event = self.library_loader.load().by_id()["E081"]
        context.state.pending_legal_event = event.to_pending_payload()
        context.state.flags["pending_sentence_years"] = sentence_years
        context.result_collector.pending_legal_event = event.to_pending_payload()
        return event.to_pending_payload()

    def submit_choice(self, context: SimulationContext, choice_id: str) -> dict[str, Any]:
        pending = context.state.pending_legal_event
        if pending is None:
            raise ValueError("No pending legal event.")

        event_id = str(pending["event_id"])
        legal = self._working(context)
        legal_rules = get_legal_rules(context.rules)
        result: dict[str, Any] = {"event_id": event_id, "choice_id": choice_id}

        if event_id == "E081" and choice_id == "E081_A":
            years = int(context.state.flags.pop("pending_sentence_years", 4))
            self._apply_sentencing(legal, years, context.state.age)
            result["sentence_years"] = years
        elif event_id == "E082":
            result.update(self._handle_prison_year_choice(context, legal, legal_rules, choice_id))
        elif event_id == "E089":
            result.update(self._handle_fugitive_choice(context, legal, legal_rules, choice_id))
            self._apply_recapture(context, legal, legal_rules)
        else:
            raise ValueError(f"Unsupported legal choice: {event_id}/{choice_id}")

        context.state.pending_legal_event = None
        context.result_collector.pending_legal_event = None
        self._publish_update(context, legal, f"{event_id}:{choice_id}")
        return result

    def _handle_prison_year_choice(
        self,
        context: SimulationContext,
        legal: LegalState,
        legal_rules: dict,
        choice_id: str,
    ) -> dict[str, Any]:
        outcome: dict[str, Any] = {"choice_id": choice_id}

        if choice_id == "E082_A":
            gain = context.rng.randint(
                int(legal_rules["rehabilitation_gain_min"]),
                int(legal_rules["rehabilitation_gain_max"]),
            )
            legal.rehabilitation_progress += int(gain * legal.rehabilitation_gain_multiplier)
            legal.consecutive_rehabilitation_years += 1
            legal.sentence_reduction_counter += 1
            legal.last_legal_event = "E083"
            self._record_history(legal, "E083", {"gain": gain})
            outcome["rehabilitation_gain"] = gain
            self._serve_one_year(legal)
            if self._try_short_sentence_release(legal, legal_rules, context):
                outcome["early_release"] = True
                self._apply_formal_release(context, legal, legal_rules, supervision=True)
            else:
                self._try_sentence_reduction(context, legal, legal_rules, outcome)
        elif choice_id == "E082_B":
            legal.consecutive_rehabilitation_years = 0
            legal.last_legal_event = "E082"
            self._serve_one_year(legal)
        elif choice_id == "E082_C":
            legal.consecutive_rehabilitation_years = 0
            legal.rehabilitation_progress = 0
            escape_outcome = self._attempt_escape(context, legal, legal_rules)
            outcome.update(escape_outcome)
            if legal.is_in_prison:
                self._serve_one_year(legal)
        else:
            raise ValueError(f"Unknown prison choice: {choice_id}")

        if legal.sentence_remaining_years <= 0 and legal.is_in_prison:
            self._apply_formal_release(context, legal, legal_rules, supervision=False)
            outcome["released"] = True

        return outcome

    def _handle_fugitive_choice(
        self,
        context: SimulationContext,
        legal: LegalState,
        legal_rules: dict,
        choice_id: str,
    ) -> dict[str, Any]:
        income_map = {
            "E089_A": float(legal_rules.get("fugitive_labor_income_low", 3000)),
            "E089_B": float(legal_rules.get("fugitive_labor_income_medium", 6000)),
            "E089_C": float(legal_rules.get("fugitive_labor_income_minimal", 1000)),
        }
        stress_map = {"E089_A": -3, "E089_B": -6, "E089_C": -1}
        risk_map = {"E089_A": 1.0, "E089_B": 1.5, "E089_C": 0.7}

        income = income_map.get(choice_id, 3000.0)
        context.event_bus.publish(
            SimulationEventType.ASSET_CHANGE_REQUESTED,
            self.name,
            {"key": "cash", "delta": income, "reason": "fugitive_labor"},
        )
        context.event_bus.publish(
            SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED,
            self.name,
            {"key": "stress_resistance", "delta": stress_map.get(choice_id, -3), "reason": "fugitive_pressure"},
        )
        legal.recapture_risk_modifier = risk_map.get(choice_id, 1.0)
        legal.last_legal_event = "E089"
        return {"income": income, "choice_id": choice_id}

    def _apply_sentencing(self, legal: LegalState, years: int, age: int) -> None:
        legal.is_in_prison = True
        legal.sentence_total_years = years
        legal.sentence_remaining_years = years
        legal.years_served = 0
        legal.has_criminal_record = True
        legal.civil_service_banned = True
        legal.education_locked = True
        legal.career_locked = True
        legal.normal_job_locked = True
        legal.is_fugitive = False
        legal.is_under_supervision = False
        legal.last_legal_event = "E081"
        self._record_history(legal, "E081", {"sentence_years": years, "age": age})

    def _serve_one_year(self, legal: LegalState) -> None:
        legal.sentence_remaining_years = max(0, legal.sentence_remaining_years - 1)
        legal.years_served += 1

    def _try_short_sentence_release(
        self,
        legal: LegalState,
        legal_rules: dict,
        context: SimulationContext,
    ) -> bool:
        threshold = int(legal_rules["short_sentence_threshold_years"])
        years_needed = int(legal_rules["short_sentence_release_after_consecutive_rehabilitation_years"])
        if (
            legal.sentence_total_years < threshold
            and legal.consecutive_rehabilitation_years >= years_needed
        ):
            legal.last_legal_event = "E085"
            self._record_history(legal, "E085", {"auto_release": True})
            return True
        return False

    def _try_sentence_reduction(
        self,
        context: SimulationContext,
        legal: LegalState,
        legal_rules: dict,
        outcome: dict[str, Any],
    ) -> None:
        min_years = int(legal_rules["minimum_years_before_reduction"])
        mandatory = int(legal_rules["mandatory_reduction_after_consecutive_rehabilitation_years"])
        if legal.years_served < min_years and legal.consecutive_rehabilitation_years < mandatory:
            return

        progress = legal.rehabilitation_progress
        bonus_threshold = int(legal_rules["progress_bonus_threshold"])
        if progress <= bonus_threshold:
            ratio = float(legal_rules["normal_reduction_ratio"])
        else:
            ratio = (progress - 100) / 100.0

        reduction_years = max(1, math.floor(legal.sentence_total_years * ratio))
        legal.sentence_remaining_years = max(0, legal.sentence_remaining_years - reduction_years)
        legal.rehabilitation_progress = 0
        legal.sentence_reduction_counter = 0
        legal.last_legal_event = "E084"
        self._record_history(
            legal,
            "E084",
            {"ratio": ratio, "reduction_years": reduction_years},
        )
        outcome["sentence_reduction_years"] = reduction_years
        outcome["reduction_ratio"] = ratio

    def _attempt_escape(
        self,
        context: SimulationContext,
        legal: LegalState,
        legal_rules: dict,
    ) -> dict[str, Any]:
        legal.last_legal_event = "E086"
        success_prob = float(legal_rules["escape_success_probability"])
        if context.rng.random() <= success_prob:
            legal.is_in_prison = False
            legal.is_fugitive = True
            legal.escape_succeeded = True
            legal.education_locked = True
            legal.career_locked = True
            legal.normal_job_locked = True
            legal.startup_restriction_active = True
            legal.last_legal_event = "E088"
            self._record_history(legal, "E088", {"escaped": True})
            return {"escape": "success"}
        ratio = float(legal_rules["escape_failure_sentence_increase_ratio"])
        increase = max(1, math.ceil(legal.sentence_remaining_years * ratio))
        legal.sentence_remaining_years += increase
        legal.rehabilitation_progress = 0
        legal.consecutive_rehabilitation_years = 0
        legal.escape_attempt_count += 1
        legal.last_legal_event = "E087"
        self._record_history(legal, "E087", {"increase": increase})
        return {"escape": "failed", "sentence_increase": increase}

    def _apply_recapture(
        self,
        context: SimulationContext,
        legal: LegalState,
        legal_rules: dict,
    ) -> None:
        if not legal.is_fugitive:
            return
        ratio = float(legal_rules["recapture_sentence_increase_ratio"])
        increase = max(1, math.ceil(legal.sentence_remaining_years * ratio))
        legal.is_fugitive = False
        legal.is_in_prison = True
        legal.sentence_remaining_years += increase
        legal.rehabilitation_progress = 0
        legal.consecutive_rehabilitation_years = 0
        legal.education_locked = True
        legal.career_locked = True
        legal.normal_job_locked = True
        legal.last_legal_event = "E090"
        self._record_history(legal, "E090", {"sentence_increase": increase})

    def _apply_formal_release(
        self,
        context: SimulationContext,
        legal: LegalState,
        legal_rules: dict,
        *,
        supervision: bool,
    ) -> None:
        legal.is_in_prison = False
        legal.is_fugitive = False
        legal.sentence_remaining_years = 0
        legal.has_criminal_record = True
        legal.civil_service_banned = bool(legal_rules.get("civil_service_banned_after_release", True))
        legal.research_job_ban_remaining_years = int(
            legal_rules.get("research_job_ban_years_after_release", 10)
        )
        legal.post_release_employment_penalty_year = 1
        legal.years_after_release = 0
        legal.release_age = context.state.age
        legal.release_year = context.state.age
        legal.education_locked = False
        legal.last_legal_event = "E091"
        self._record_history(legal, "E091", {"release_age": legal.release_age})

        if supervision:
            legal.is_under_supervision = True
            legal.supervision_remaining_years = int(
                legal_rules.get("supervision_years_after_short_sentence_release", 1)
            )
            legal.normal_job_locked = True
            legal.career_locked = True
            self._record_history(legal, "E092", {"years": legal.supervision_remaining_years})
        else:
            legal.career_locked = False
            legal.normal_job_locked = False

    def _set_pending(self, context: SimulationContext, event_id: str) -> None:
        event = self.library_loader.load().by_id()[event_id]
        payload = event.to_pending_payload()
        context.result_collector.pending_legal_event = payload

    def _working(self, context: SimulationContext) -> LegalState:
        if context.result_collector._legal_working is None:
            context.result_collector.bind_legal_context(context.state)
        return context.result_collector._legal_working

    def _publish_update(self, context: SimulationContext, legal: LegalState, reason: str) -> None:
        context.event_bus.publish(
            SimulationEventType.LEGAL_STATE_UPDATE_REQUESTED,
            self.name,
            {"legal": legal.to_life_state_dict(), "reason": reason},
        )

    def _record_history(self, legal: LegalState, event_id: str, details: dict[str, Any]) -> None:
        legal.legal_history.append({"event_id": event_id, **details})

    def get_restrictions_summary(self, legal: LegalState, rules: dict) -> dict[str, Any]:
        return {
            "employment_penalty_rate": legal.employment_penalty_rate(rules),
            "research_job_banned": legal.research_job_ban_remaining_years > 0,
            "civil_service_banned": legal.civil_service_banned,
            "normal_job_locked": legal.normal_job_locked,
            "education_locked": legal.education_locked,
            "startup_restriction_active": legal.startup_restriction_active,
        }

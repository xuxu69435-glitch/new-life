from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.career.models import CareerState
from app.modules.career.rules import (
    build_default_career_state,
    calculate_annual_income,
    get_career_rules,
    get_path_by_id,
    resolve_position_level,
    select_career_path,
)
from app.modules.education.models import EducationState
from app.modules.legal.models import LegalState
from app.modules.legal.rules import blocks_normal_career


class CareerService:
    name = "career"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        if context.state.is_dead:
            return

        legal = LegalState.from_life_state_dict(context.state.legal)
        if blocks_normal_career(legal, context.rules):
            return

        rules = context.rules
        career_rules = get_career_rules(rules)
        age = context.state.age
        next_age = age + 1
        education = EducationState.from_life_state_dict(context.state.education, rules)
        career = CareerState.from_life_state_dict(context.state.career, rules)
        status_before = career.employment_status
        income_delta = 0.0

        retirement_age = int(career_rules.get("retirement_age", 65))
        min_work_age = int(career_rules.get("min_work_age", 18))

        if next_age >= retirement_age:
            career.employment_status = "retired"
            career.is_retired = True
            career.annual_income = 0.0
            career.last_income_change = 0.0
        elif education.is_enrolled and not education.is_graduated:
            career.employment_status = "student"
            career.career_path = ""
            career.position_level = ""
            career.annual_income = 0.0
            career.last_income_change = 0.0
        elif next_age >= min_work_age:
            if career.employment_status != "employed" or not career.career_path:
                path_id = select_career_path(education.highest_level, rules)
                career.career_path = path_id
                career.employment_status = "employed"
                career.years_worked = 0
                career.history.append(
                    {
                        "age": next_age,
                        "event": "hired",
                        "career_path": path_id,
                        "highest_level": education.highest_level,
                    }
                )

            path = get_path_by_id(career.career_path, rules)
            if path is not None:
                career.years_worked += 1
                career.position_level = resolve_position_level(path, career.years_worked)
                career.annual_income = calculate_annual_income(
                    path,
                    career.years_worked,
                    education.highest_level,
                    rules,
                )
                income_delta = career.annual_income
                career.last_income_change = income_delta
                context.event_bus.publish(
                    SimulationEventType.ASSET_CHANGE_REQUESTED,
                    self.name,
                    {
                        "key": "cash",
                        "delta": income_delta,
                        "source_event_id": career.career_path,
                        "reason": f"Annual income from {career.career_path}",
                    },
                )
        else:
            career.employment_status = "unemployed"
            career.career_path = ""
            career.position_level = ""
            career.annual_income = 0.0
            career.last_income_change = 0.0

        context.event_bus.publish(
            SimulationEventType.CAREER_PROGRESSED,
            self.name,
            {
                "employment_status": career.employment_status,
                "career_path": career.career_path,
                "annual_income": career.annual_income,
            },
        )
        context.event_bus.publish(
            SimulationEventType.CAREER_STATE_UPDATE_REQUESTED,
            self.name,
            {
                "career": career.to_life_state_dict(),
                "career_status_before": status_before,
                "career_status_after": career.employment_status,
                "career_path": career.career_path,
                "position_level": career.position_level,
                "annual_income": career.annual_income,
                "career_income_change": income_delta,
            },
        )

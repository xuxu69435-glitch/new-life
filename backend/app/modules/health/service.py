from app.engine.simulation_context import SimulationContext, SimulationEventType
from app.modules.health.models import HealthState
from app.modules.health.rules import (
    calculate_natural_death_probability,
    can_enter_high_longevity,
    get_annual_decay,
    get_disease_pool,
    get_longevity_config,
    get_rest_focus_recovery,
    get_warning_config,
    has_natural_death_foreshadowing,
    resolve_health_level,
    sync_warning_counters,
)


class HealthService:
    name = "health"
    can_confirm_death = False

    def run(self, context: SimulationContext) -> None:
        rules = context.rules
        age = context.state.age
        health_state = HealthState.from_life_state_dict(context.state.health, rules)
        score_before = health_state.health_score
        level_before = health_state.health_level

        decay = get_annual_decay(context.state.life_stage, rules)
        health_delta = -decay

        if context.player_choices.get("annual_focus") == "rest_focus":
            health_delta += get_rest_focus_recovery(rules)

        if health_delta != 0:
            health_state.health_score += health_delta
            health_state.last_health_change = health_delta
            health_state.clamp_score(rules)
            context.event_bus.publish(
                SimulationEventType.HEALTH_CHANGE_REQUESTED,
                self.name,
                {"key": "health_score", "delta": health_delta},
            )

        level_rule = resolve_health_level(health_state.health_score, rules)
        health_state.health_level = level_rule["name"]
        health_state.natural_life_floor = int(level_rule["natural_life_floor"])
        health_state.natural_death_eligible_age = int(level_rule["natural_death_eligible_age"])
        sync_warning_counters(age, health_state)

        natural_death_candidate_created = False
        if self._can_evaluate_natural_death(age, health_state, rules):
            probability = calculate_natural_death_probability(
                age,
                health_state.health_level,
                rules,
            )
            if probability > 0 and context.rng.random() <= probability:
                if has_natural_death_foreshadowing(age, health_state, rules):
                    natural_death_candidate_created = True
                    context.event_bus.publish(
                        SimulationEventType.NATURAL_DEATH_CANDIDATE_CREATED,
                        self.name,
                        {
                            "reason": "natural aging",
                            "death_type": "natural_death",
                            "probability": 1.0,
                        },
                    )
                else:
                    self._issue_foreshadowing_warning(context, health_state, age)

        context.event_bus.publish(
            SimulationEventType.HEALTH_STATE_UPDATE_REQUESTED,
            self.name,
            {
                "health": health_state.to_life_state_dict(),
                "health_score_before": score_before,
                "health_score_after": health_state.health_score,
                "health_level_before": level_before,
                "health_level_after": health_state.health_level,
                "natural_death_candidate_created": natural_death_candidate_created,
            },
        )

    def _can_evaluate_natural_death(
        self,
        age: int,
        health_state: HealthState,
        rules: dict,
    ) -> bool:
        if age < health_state.natural_life_floor:
            return False
        if age < health_state.natural_death_eligible_age:
            return False

        high_age = int(get_longevity_config(rules).get("high_longevity_check_age", 90))
        if age >= high_age:
            return can_enter_high_longevity(health_state.health_level, rules)
        return True

    def _issue_foreshadowing_warning(
        self,
        context: SimulationContext,
        health_state: HealthState,
        age: int,
    ) -> None:
        rules = context.rules
        warning_config = get_warning_config(rules)
        disease_pool = get_disease_pool(rules)
        use_decline = (
            warning_config.get("require_decline_warning_last_year", True)
            and health_state.last_disease_warning_age == age - 1
        ) or (not disease_pool)

        if use_decline:
            warning_text = str(warning_config.get("decline_warning_text", "Body decline warning"))
            health_state.last_decline_warning_age = age
            health_state.warnings.append(
                {"type": "decline", "age": age, "text": warning_text},
            )
            context.event_bus.publish(
                SimulationEventType.HEALTH_WARNING_CREATED,
                self.name,
                {"warning_type": "decline", "text": warning_text},
            )
        else:
            disease_index = int(context.rng.random() * len(disease_pool)) if disease_pool else 0
            disease = disease_pool[disease_index]
            disease_id = str(disease["id"])
            warning_text = str(disease.get("name", disease_id))
            if disease_id not in health_state.diseases:
                health_state.diseases.append(disease_id)
            health_state.last_disease_warning_age = age
            health_state.warnings.append(
                {"type": "disease", "age": age, "disease_id": disease_id, "text": warning_text},
            )
            context.event_bus.publish(
                SimulationEventType.HEALTH_WARNING_CREATED,
                self.name,
                {
                    "warning_type": "disease",
                    "disease_id": disease_id,
                    "text": warning_text,
                },
            )

        sync_warning_counters(age, health_state)

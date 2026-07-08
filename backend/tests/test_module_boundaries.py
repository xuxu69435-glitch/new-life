from app.engine.simulation_context import SimulationEventType
from app.modules.assets.service import AssetsService
from app.modules.career.service import CareerService
from app.modules.health.service import HealthService
from app.modules.random_events.service import RandomEventsService

from conftest import make_context


def test_health_module_does_not_set_death(life_state, rules) -> None:
    old_state = life_state.model_copy(update={"age": 95, "life_stage": "elder"})
    old_state.health["last_disease_warning_age"] = 93
    context = make_context(old_state, rules)

    HealthService().run(context)

    assert old_state.is_dead is False
    assert context.result_collector.death_confirmed is False


def test_random_event_module_does_not_set_death(life_state, rules) -> None:
    rules["random_events"]["event_pool"] = [
        {
            "id": "fatal_placeholder",
            "name": "Fatal placeholder",
            "category": "direct_death",
            "stage": "any",
            "probability": 1.0,
            "direct_death": True,
            "weight": 1.0,
            "death_reason": "Fatal placeholder",
            "conditions": {},
            "effects": [
                {
                    "type": "direct_death_candidate",
                    "target": "death",
                    "value": 1,
                    "reason": "Fatal placeholder",
                    "source_event_id": "fatal_placeholder",
                    "source_event_name": "Fatal placeholder",
                }
            ],
        }
    ]
    context = make_context(life_state, rules)

    RandomEventsService().run(context)

    assert life_state.is_dead is False
    assert context.result_collector.death_confirmed is False
    assert context.event_bus.by_type(SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED)


def test_career_publishes_asset_change_and_result_collector_merges_income(life_state, rules) -> None:
    from app.modules.education.models import EducationState

    adult_state = life_state.model_copy(
        update={
            "age": 29,
            "life_stage": "adult",
            "education": EducationState(
                current_stage="none",
                highest_level="high_school",
                is_enrolled=False,
                is_graduated=True,
                graduation_age=17,
            ).to_life_state_dict(),
            "career": {
                "employment_status": "employed",
                "career_path": "general_worker",
                "position_level": "junior",
                "annual_income": 12000,
                "years_worked": 1,
                "is_retired": False,
                "last_income_change": 0.0,
                "history": [],
            },
        }
    )
    context = make_context(adult_state, rules)

    CareerService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    assert context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)
    assert context.result_collector.changed_assets["cash"] > 0

from app.application.game_command_service import GameCommandService
from app.engine.simulation_context import SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.modules.mainline.models import MainlineState
from app.modules.mainline.service import MainlineService

from conftest import make_context


def _advance(engine, state, rules, years: int = 1):
    current = state
    last_result = None
    for _ in range(years):
        if current.pending_legal_event:
            current, _ = engine.submit_legal_choice(current, "E082_B", rules)
        if current.pending_random_event:
            break
        current, last_result, _ = engine.advance_one_year(
            current,
            {"annual_focus": "balanced_year"},
            rules,
        )
    return current, last_result


def test_create_life_has_stable_mainline_state() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert mainline.current_chapter == "infant"
    assert mainline.active_tasks == []
    assert mainline.completed_tasks == []


def test_m001_activates_in_infancy(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    state, result = _advance(engine, life_state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M001" in mainline.active_tasks
    assert result is not None
    assert result.active_mainline_tasks


def test_m001_completes_at_age_three_with_health(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    state = life_state.model_copy(
        update={"health": {**life_state.health, "health_score": 80}}
    )
    state, result = _advance(engine, state, rules, 3)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M001" in mainline.completed_tasks
    assert "M001" not in mainline.active_tasks
    assert "M001" in result.completed_mainline_tasks_this_year


def test_completed_task_not_reactivated(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    state = life_state.model_copy(
        update={"health": {**life_state.health, "health_score": 80}}
    )
    state, _ = _advance(engine, state, rules, 3)
    state, _ = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert mainline.active_tasks.count("M001") == 0


def test_task_rewards_publish_domain_events(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    state = life_state.model_copy(
        update={"health": {**life_state.health, "health_score": 80}}
    )
    context = make_context(state, rules)
    context.result_collector.bind_mainline_context(state)
    context.result_collector.bind_family_context(state, rules)
    context.result_collector.bind_legal_context(state)
    for _ in range(3):
        context.state = context.result_collector.snapshot_state(context.state, rules)
        MainlineService().run(context)
        context.result_collector.collect_from_events(context.event_bus.all())
    attr_events = context.event_bus.by_type(SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED)
    health_events = context.event_bus.by_type(SimulationEventType.HEALTH_CHANGE_REQUESTED)
    assert any(event.source_module == "mainline" for event in attr_events)
    assert any(event.source_module == "mainline" for event in health_events)


def test_mainline_does_not_modify_other_modules_directly(life_state, rules) -> None:
    before_education = dict(life_state.education)
    before_career = dict(life_state.career)
    context = make_context(life_state, rules)
    context.result_collector.bind_mainline_context(life_state)
    MainlineService().run(context)
    assert context.state.education == before_education
    assert context.state.career == before_career


def test_expired_task_moves_to_expired_tasks(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    state = life_state.model_copy(
        update={"health": {**life_state.health, "health_score": 30}}
    )
    state, _ = _advance(engine, state, rules, 4)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M001" in mainline.expired_tasks


def test_prison_activates_m020_not_normal_tasks(life_state, rules) -> None:
    from tests.test_legal_system import _imprison

    state, _ = _imprison(
        life_state.model_copy(update={"age": 30, "life_stage": "adult"}),
        rules,
        years=6,
    )
    engine = SimulationEngine(rng_seed=1)
    state, result = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M020" in mainline.active_tasks
    assert "M011" not in mainline.active_tasks
    assert result.current_guidance_text


def test_fugitive_pauses_normal_mainline(life_state, rules) -> None:
    legal = {
        **life_state.legal,
        "is_fugitive": True,
        "sentence_remaining_years": 5,
        "education_locked": True,
        "career_locked": True,
    }
    state = life_state.model_copy(
        update={"age": 30, "life_stage": "adult", "legal": legal}
    )
    engine = SimulationEngine(rng_seed=1)
    state, _ = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "潜逃" in mainline.current_guidance_text
    assert "M011" not in mainline.active_tasks


def test_m021_activates_after_release(life_state, rules) -> None:
    legal = {
        **life_state.legal,
        "has_criminal_record": True,
        "is_in_prison": False,
        "is_fugitive": False,
        "is_under_supervision": True,
        "supervision_remaining_years": 2,
    }
    state = life_state.model_copy(
        update={"age": 35, "life_stage": "adult", "legal": legal}
    )
    engine = SimulationEngine(rng_seed=1)
    state, _ = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M021" in mainline.active_tasks or "M021" in mainline.completed_tasks


def test_death_stops_new_mainline_activation(life_state, rules) -> None:
    state = life_state.model_copy(update={"is_dead": True, "death_reason": "test"})
    engine = SimulationEngine(rng_seed=1)
    context = make_context(state, rules)
    context.result_collector.bind_mainline_context(state)
    MainlineService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())
    mainline = context.result_collector._mainline_working
    assert mainline.active_tasks == []


def test_m011_completes_when_employed(life_state, rules) -> None:
    education = {
        **life_state.education,
        "current_stage": "none",
        "is_enrolled": False,
        "is_graduated": True,
        "highest_level": "high_school",
    }
    career = {
        **life_state.career,
        "employment_status": "employed",
        "annual_income": 12000,
        "career_path": "office_worker",
    }
    state = life_state.model_copy(
        update={
            "age": 25,
            "life_stage": "adult",
            "education": education,
            "career": career,
        }
    )
    engine = SimulationEngine(rng_seed=1)
    state, result = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M011" in mainline.completed_tasks
    assert result.mainline_rewards


def test_m012_completes_when_cash_sufficient(life_state, rules) -> None:
    assets = {**life_state.assets, "cash": 12000.0, "net_worth": 12000.0}
    state = life_state.model_copy(
        update={"age": 28, "life_stage": "adult", "assets": assets}
    )
    engine = SimulationEngine(rng_seed=1)
    state, _ = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M012" in mainline.completed_tasks


def test_m014_completes_when_married(life_state, rules) -> None:
    family = {
        **life_state.family,
        "relationship_status": "married",
        "spouse": {
            "person_id": "spouse-1",
            "name": "Partner",
            "relation": "spouse",
            "playable": False,
        },
    }
    state = life_state.model_copy(
        update={"age": 30, "life_stage": "adult", "family": family}
    )
    engine = SimulationEngine(rng_seed=1)
    state, _ = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M014" in mainline.completed_tasks


def test_m015_completes_with_children(life_state, rules) -> None:
    family = {
        **life_state.family,
        "relationship_status": "married",
        "children_count": 1,
        "children": [
            {
                "person_id": "child-1",
                "name": "Child",
                "relation": "child",
                "playable": True,
            }
        ],
    }
    state = life_state.model_copy(
        update={"age": 32, "life_stage": "adult", "family": family}
    )
    engine = SimulationEngine(rng_seed=1)
    state, _ = _advance(engine, state, rules, 1)
    mainline = MainlineState.from_life_state_dict(state.mainline)
    assert "M015" in mainline.completed_tasks


def test_year_result_returns_mainline_fields(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, life_state, rules, 1)
    assert hasattr(result, "active_mainline_tasks")
    assert hasattr(result, "completed_mainline_tasks_this_year")
    assert hasattr(result, "current_guidance_text")


def test_mainline_rules_load_from_v1(rules) -> None:
    assert rules["mainline"]["use_mainline_v1"] is True
    assert rules["mainline"]["mainline_version"] == "v1"

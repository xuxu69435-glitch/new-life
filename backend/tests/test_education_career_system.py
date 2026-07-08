from app.application.game_command_service import GameCommandService
from app.application.save_service import SaveService
from app.engine.simulation_context import SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.modules.career.service import CareerService
from app.modules.education.models import EducationState
from app.modules.education.rules import build_default_education_state, resolve_stage_for_age
from app.modules.education.service import EducationService
from app.modules.career.rules import build_default_career_state, select_career_path
from app.rules.rule_loader import RuleLoader

from conftest import make_context


def test_education_rules_load_from_v1(rules) -> None:
    assert rules["education"]["stages"]
    assert len(rules["education"]["stages"]) >= 5


def test_career_rules_load_from_v1(rules) -> None:
    assert rules["career"]["paths"]
    assert rules["career"]["education_to_career_mapping"]
    assert rules["career"]["retirement_age"] == 65


def test_create_life_has_stable_education_and_career_state() -> None:
    service = GameCommandService()
    state, _choices = service.create_life()

    assert "current_stage" in state.education
    assert "highest_level" in state.education
    assert "employment_status" in state.career
    assert "annual_income" in state.career


def test_age_enters_primary_school(rules) -> None:
    stage = resolve_stage_for_age(7, rules)
    assert stage is not None
    assert stage["id"] == "primary_school"


def test_age_enters_middle_school(rules) -> None:
    stage = resolve_stage_for_age(13, rules)
    assert stage["id"] == "middle_school"


def test_age_enters_high_school(rules) -> None:
    stage = resolve_stage_for_age(16, rules)
    assert stage["id"] == "high_school"


def test_age_enters_college(rules) -> None:
    stage = resolve_stage_for_age(19, rules)
    assert stage["id"] == "college"


def test_age_enters_none_stage(rules) -> None:
    stage = resolve_stage_for_age(25, rules)
    assert stage["id"] == "none"


def test_education_progress_publishes_attribute_change_requested(life_state, rules) -> None:
    child_state = life_state.model_copy(update={"age": 10, "life_stage": "childhood"})
    context = make_context(child_state, rules)

    EducationService().run(context)

    assert context.event_bus.by_type(SimulationEventType.ATTRIBUTE_CHANGE_REQUESTED)
    assert child_state.attributes == life_state.attributes


def test_education_module_does_not_modify_attributes_directly(life_state, rules) -> None:
    before = dict(life_state.attributes)
    context = make_context(life_state, rules)
    EducationService().run(context)
    assert context.state.attributes == before


def test_graduation_updates_education_state(life_state, rules) -> None:
    state = life_state.model_copy(
        update={
            "age": 16,
            "education": EducationState(
                current_stage="high_school",
                current_track="standard",
                school_year=2,
                highest_level="middle_school",
                is_enrolled=True,
                is_graduated=False,
            ).to_life_state_dict(),
        }
    )
    context = make_context(state, rules)
    EducationService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    assert context.result_collector.education_graduated_this_year is True
    assert context.result_collector.education_state_update["highest_level"] == "high_school"


def test_student_stage_has_no_career_income(life_state, rules) -> None:
    student_state = life_state.model_copy(
        update={
            "age": 15,
            "education": EducationState(
                current_stage="high_school",
                is_enrolled=True,
                is_graduated=False,
            ).to_life_state_dict(),
        }
    )
    context = make_context(student_state, rules)
    CareerService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    assert not context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)
    assert context.result_collector.career_status_after == "student"


def test_working_age_enters_default_career_path(life_state, rules) -> None:
    adult_state = life_state.model_copy(
        update={
            "age": 21,
            "education": EducationState(
                current_stage="college",
                highest_level="college",
                is_enrolled=False,
                is_graduated=True,
                graduation_age=21,
            ).to_life_state_dict(),
            "career": build_default_career_state(rules).to_life_state_dict(),
        }
    )
    context = make_context(adult_state, rules)
    CareerService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    assert context.result_collector.career_status_after == "employed"
    assert context.result_collector.career_path


def test_career_income_published_via_asset_change_requested(life_state, rules) -> None:
    adult_state = life_state.model_copy(
        update={
            "age": 25,
            "education": EducationState(
                highest_level="high_school",
                is_enrolled=False,
                is_graduated=True,
            ).to_life_state_dict(),
            "career": {
                "employment_status": "employed",
                "career_path": "general_worker",
                "position_level": "junior",
                "annual_income": 0.0,
                "years_worked": 0,
                "is_retired": False,
                "last_income_change": 0.0,
                "history": [],
            },
        }
    )
    context = make_context(adult_state, rules)
    CareerService().run(context)

    events = context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)
    assert events
    assert events[0].source_module == "career"
    assert life_state.assets.get("cash", 0) == 0


def test_career_module_does_not_modify_assets_directly(life_state, rules) -> None:
    before_cash = float(life_state.assets.get("cash", 0.0))
    adult_state = life_state.model_copy(
        update={
            "age": 30,
            "education": EducationState(highest_level="high_school", is_graduated=True).to_life_state_dict(),
            "career": {
                "employment_status": "employed",
                "career_path": "general_worker",
                "years_worked": 2,
                "is_retired": False,
                "history": [],
            },
        }
    )
    context = make_context(adult_state, rules)
    CareerService().run(context)
    assert float(context.state.assets.get("cash", 0.0)) == before_cash


def test_college_education_affects_career_path(rules) -> None:
    path = select_career_path("college", rules)
    assert path in {"office_worker", "technical_worker", "freelancer"}
    assert path != "general_worker" or "general_worker" in rules["career"]["education_to_career_mapping"]["college"]


def test_year_result_includes_education_and_career_changes(life_state, rules) -> None:
    state = life_state.model_copy(
        update={
            "age": 29,
            "life_stage": "adult",
            "education": EducationState(
                highest_level="high_school",
                is_graduated=True,
                is_enrolled=False,
            ).to_life_state_dict(),
            "career": {
                "employment_status": "employed",
                "career_path": "general_worker",
                "years_worked": 1,
                "is_retired": False,
                "history": [],
            },
        }
    )
    engine = SimulationEngine(rng_seed=1)
    next_state, result, _inheritance = engine.advance_one_year(
        state,
        {"annual_focus": "balanced_year"},
        rules,
    )

    assert result.education_stage_after is not None
    assert result.career_status_after is not None
    assert result.career_income_change >= 0
    assert next_state.education.get("current_stage") is not None
    assert next_state.career.get("employment_status") is not None


def test_save_service_initializes_education_from_rules(rules) -> None:
    education = build_default_education_state(rules)
    assert education.current_stage == "preschool"
    assert education.is_enrolled is True

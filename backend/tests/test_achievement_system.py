import pytest
from unittest.mock import MagicMock

from app.application.game_command_service import GameCommandService
from app.engine.simulation_context import LifeState, SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.modules.achievement.condition_evaluator import AchievementConditionEvaluator, AchievementConditionError
from app.modules.achievement.models import AchievementState
from app.modules.achievement.service import AchievementService
from app.modules.death.service import DeathService
from app.modules.inheritance.service import InheritanceService
from app.rules.achievement_library_loader import AchievementLibraryLoader
from app.rules.achievement_validator import AchievementValidator

from conftest import make_context


def test_create_life_has_stable_achievement_state() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    achievement = AchievementState.from_life_state_dict(state.achievements)
    assert achievement.unlocked_achievements == []
    assert achievement.achievement_points == 0
    assert achievement.milestones


def test_achievement_library_loads() -> None:
    library = AchievementLibraryLoader().load()
    assert library.achievement_count == 32
    AchievementValidator().validate_library(library)


def test_duplicate_achievement_id_validation_fails() -> None:
    library = AchievementLibraryLoader().load()
    library.achievements.append(library.achievements[0].model_copy())
    with pytest.raises(Exception):
        AchievementValidator().validate_library(library)


def test_unknown_condition_field_validation_fails() -> None:
    library = AchievementLibraryLoader().load()
    library.achievements[0].unlock_conditions = {"unknown_field": True}
    with pytest.raises(Exception):
        AchievementValidator().validate_library(library)


def test_unknown_condition_evaluator_raises() -> None:
    with pytest.raises(AchievementConditionError):
        AchievementConditionEvaluator().matches({"bad_key": 1}, LifeState(life_id="x", person_id="p"), AchievementState())


def _advance(engine, state, rules, years=1):
    current = state
    last = None
    for _ in range(years):
        current, last, _ = engine.advance_one_year(current, {"annual_focus": "balanced_year"}, rules)
    return current, last


def test_a001_unlocks_after_first_year(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, life_state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A001" in ids


def test_a003_unlocks_at_eighteen(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    state = life_state.model_copy(update={"age": 17, "life_stage": "teen"})
    _, result = _advance(engine, state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A003" in ids


def test_a008_unlocks_when_employed(life_state, rules) -> None:
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
        "annual_income": 18000,
        "career_path": "office_worker",
    }
    state = life_state.model_copy(
        update={"age": 25, "life_stage": "adult", "education": education, "career": career}
    )
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, state, rules, 1)
    unlocked_ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A008" in unlocked_ids


def test_a016_unlocks_when_married(life_state, rules) -> None:
    family = {
        **life_state.family,
        "relationship_status": "married",
        "spouse": {"person_id": "s1", "name": "Spouse", "relation": "spouse", "playable": False},
    }
    state = life_state.model_copy(update={"age": 30, "life_stage": "adult", "family": family})
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A016" in ids


def test_a017_unlocks_with_children(life_state, rules) -> None:
    family = {
        **life_state.family,
        "children_count": 1,
        "children": [{"person_id": "c1", "name": "Child", "relation": "child", "playable": True}],
    }
    state = life_state.model_copy(update={"age": 32, "life_stage": "adult", "family": family})
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A017" in ids


def test_a023_unlocks_with_criminal_record(life_state, rules) -> None:
    legal = {**life_state.legal, "has_criminal_record": True}
    state = life_state.model_copy(update={"age": 30, "life_stage": "adult", "legal": legal})
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A023" in ids


def test_a026_unlocks_with_rehabilitation(life_state, rules) -> None:
    legal = {
        **life_state.legal,
        "is_in_prison": True,
        "has_criminal_record": True,
        "consecutive_rehabilitation_years": 3,
    }
    state = life_state.model_copy(update={"age": 30, "life_stage": "adult", "legal": legal})
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A026" in ids


def test_a027_unlocks_with_mainline_completion(life_state, rules) -> None:
    mainline = {
        **life_state.mainline,
        "completed_tasks": ["M001"],
    }
    state = life_state.model_copy(update={"age": 5, "life_stage": "childhood", "mainline": mainline})
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A027" in ids


def test_unlocked_achievement_not_repeated(life_state, rules) -> None:
    achievements = {
        **build_default_dict(),
        "unlocked_achievements": ["A001"],
        "achievement_points": 5,
    }
    state = life_state.model_copy(update={"age": 2, "achievements": achievements})
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, state, rules, 1)
    ids = [item["achievement_id"] for item in result.newly_unlocked_achievements]
    assert "A001" not in ids


def test_achievement_points_accumulate(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    state, result = _advance(engine, life_state, rules, 1)
    achievement = AchievementState.from_life_state_dict(state.achievements)
    assert achievement.achievement_points >= 5
    assert result.achievement_points_gained >= 5


def test_hidden_achievement_masked_in_public_list(life_state, rules) -> None:
    service = AchievementService()
    achievement = AchievementState()
    public = service.get_public_achievements(achievement, rules)
    hidden = next(item for item in public if item["achievement_id"] == "A023")
    assert hidden["hidden"] is True
    assert hidden["unlocked"] is False
    assert hidden["title"] == "未发现"


def test_milestone_records_marriage(life_state, rules) -> None:
    family = {
        **life_state.family,
        "relationship_status": "married",
        "spouse": {"person_id": "s1", "name": "Spouse", "relation": "spouse", "playable": False},
    }
    state = life_state.model_copy(update={"age": 30, "life_stage": "adult", "family": family})
    engine = SimulationEngine(rng_seed=1)
    state, result = _advance(engine, state, rules, 1)
    milestone_ids = [item["milestone_id"] for item in result.milestones_this_year]
    achievement = AchievementState.from_life_state_dict(state.achievements)
    assert "marriage" in milestone_ids or achievement.has_milestone("marriage")


def test_milestone_records_imprisonment(life_state, rules) -> None:
    legal = {**life_state.legal, "is_in_prison": True, "has_criminal_record": True}
    state = life_state.model_copy(update={"age": 30, "life_stage": "adult", "legal": legal})
    engine = SimulationEngine(rng_seed=1)
    state, result = _advance(engine, state, rules, 1)
    achievement = AchievementState.from_life_state_dict(state.achievements)
    assert achievement.has_milestone("imprisonment") or any(
        m.get("milestone_id") == "imprisonment" for m in result.milestones_this_year
    )


def test_year_result_returns_newly_unlocked(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    _, result = _advance(engine, life_state, rules, 1)
    assert hasattr(result, "newly_unlocked_achievements")
    assert hasattr(result, "achievement_points_gained")


def test_achievement_service_does_not_modify_other_modules(life_state, rules) -> None:
    before = life_state.model_copy(deep=True)
    context = make_context(life_state, rules)
    context.result_collector.bind_achievement_context(life_state)
    context.result_collector.bind_family_context(life_state, rules)
    context.result_collector.bind_legal_context(life_state)
    context.result_collector.bind_mainline_context(life_state)
    AchievementService().run(context)
    assert context.state.education == before.education
    assert context.state.career == before.career


def build_default_dict():
    from app.modules.achievement.rules import build_default_achievement_state
    from app.rules.rule_loader import RuleLoader

    return build_default_achievement_state(RuleLoader().load("v1")).to_life_state_dict()


def test_a029_unlocks_on_death_with_inheritance(life_state, rules) -> None:
    state = life_state.model_copy(
        update={
            "age": 70,
            "life_stage": "elder",
            "assets": {"cash": 50000.0, "property_value": 0.0, "debt": 0.0, "net_worth": 50000.0},
            "family": {
                **life_state.family,
                "spouse": {"person_id": "s1", "name": "Spouse", "relation": "spouse", "playable": False},
            },
        }
    )
    context = make_context(state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)
    context.result_collector.bind_achievement_context(state)
    context.result_collector.bind_family_context(state, rules)
    context.result_collector.bind_legal_context(state)
    context.result_collector.bind_mainline_context(state)
    context.event_bus.publish(
        SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED,
        "random_events",
        {"reason": "accident", "death_type": "direct_death", "probability": 1.0},
    )
    DeathService().run(context)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})
    InheritanceService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())
    AchievementService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    unlocked_ids = [
        item["achievement_id"]
        for item in context.result_collector.newly_unlocked_achievements
    ]
    assert "A029" in unlocked_ids


def test_milestone_records_death(life_state, rules) -> None:
    state = life_state.model_copy(update={"age": 80, "life_stage": "elder"})
    context = make_context(state, rules)
    context.result_collector.bind_achievement_context(state)
    context.result_collector.bind_family_context(state, rules)
    context.result_collector.bind_legal_context(state)
    context.result_collector.bind_mainline_context(state)
    context.result_collector.confirm_death("natural", death_type="natural_death")
    AchievementService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())

    achievement = AchievementState.from_life_state_dict(context.result_collector.achievement_changes)
    assert achievement.has_milestone("death")


def test_newly_unlocked_this_year_only_current_year(life_state, rules) -> None:
    achievements = {
        **build_default_dict(),
        "unlocked_achievements": ["A001"],
        "achievement_points": 5,
        "achievement_history": [
            {
                "achievement_id": "A001",
                "title": "平安出生",
                "description": "test",
                "age": 1,
                "source": "achievement",
            }
        ],
    }
    state = life_state.model_copy(update={"age": 2, "achievements": achievements})
    engine = SimulationEngine(rng_seed=1)
    state_after, result = _advance(engine, state, rules, 1)
    achievement = AchievementState.from_life_state_dict(state_after.achievements)
    assert "A001" not in achievement.newly_unlocked_this_year
    assert all(item["achievement_id"] != "A001" for item in result.newly_unlocked_achievements)


def test_achievement_rules_load(rules) -> None:
    assert rules["achievements"]["use_achievement_v1"] is True

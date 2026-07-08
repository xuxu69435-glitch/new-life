import math

import pytest

from app.application.game_command_service import GameCommandService
from app.engine.simulation_context import SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.infrastructure.errors import PendingLegalEventError
from app.infrastructure.rng import ServerRandom
from app.modules.career.service import CareerService
from app.modules.education.service import EducationService
from app.modules.legal.models import LegalState
from app.modules.legal.rules import build_default_legal_state
from app.modules.legal.service import LegalService
from app.modules.random_events.service import RandomEventsService

from conftest import make_context


def _adult_state(life_state):
    return life_state.model_copy(update={"age": 30, "life_stage": "adult"})


def _imprison(state, rules, years: int = 8, seed: int = 1):
    engine = SimulationEngine(rng_seed=seed)
    context = make_context(state, rules, seed=seed)
    context.result_collector.bind_legal_context(state)
    LegalService().begin_sentencing(context, years)
    state.pending_legal_event = context.result_collector.pending_legal_event
    state.flags["pending_sentence_years"] = years
    return engine.submit_legal_choice(state, "E081_A", rules)


def test_create_life_has_stable_legal_state() -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    legal = LegalState.from_life_state_dict(state.legal)
    assert legal.is_in_prison is False
    assert legal.is_fugitive is False
    assert legal.has_criminal_record is False
    assert legal.sentence_total_years == 0
    assert legal.education_locked is False
    assert legal.career_locked is False


def test_legal_rules_load_from_v1(rules) -> None:
    assert rules["legal"]["escape_success_probability"] == 0.05
    assert rules["legal"]["employment_penalty_by_year"]["1"] == 0.30


def test_sentencing_sets_prison_state(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=6)
    legal = LegalState.from_life_state_dict(state.legal)
    assert legal.is_in_prison is True
    assert legal.has_criminal_record is True
    assert legal.education_locked is True
    assert legal.career_locked is True
    assert legal.sentence_total_years == 6
    assert legal.sentence_remaining_years == 6


def test_prison_blocks_education(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules)
    context = make_context(state, rules)
    EducationService().run(context)
    assert not context.event_bus.by_type(SimulationEventType.EDUCATION_STATE_UPDATE_REQUESTED)


def test_prison_blocks_career_income(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules)
    context = make_context(state, rules)
    CareerService().run(context)
    assert not context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)


def test_prison_blocks_random_events(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules)
    context = make_context(state, rules)
    RandomEventsService().run(context)
    assert not context.event_bus.by_type(SimulationEventType.RANDOM_EVENT_TRIGGERED)


def test_prison_year_returns_e082(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules)
    engine = SimulationEngine(rng_seed=1)
    next_state, year_result, _ = engine.advance_one_year(
        state,
        {"annual_focus": "balanced_year"},
        rules,
    )
    assert year_result.pending_legal_event is not None
    assert year_result.pending_legal_event["event_id"] == "E082"
    assert next_state.pending_legal_event["event_id"] == "E082"


def test_advance_blocked_when_pending_legal_event(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules)
    engine = SimulationEngine(rng_seed=1)
    next_state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    with pytest.raises(PendingLegalEventError):
        engine.advance_one_year(next_state, {"annual_focus": "balanced_year"}, rules)


def test_active_reform_increases_progress(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=8)
    engine = SimulationEngine(rng_seed=1)
    state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    next_state, result = engine.submit_legal_choice(state, "E082_A", rules)
    legal = LegalState.from_life_state_dict(next_state.legal)
    assert 10 <= result["rehabilitation_gain"] <= 50
    assert legal.consecutive_rehabilitation_years == 1
    assert legal.rehabilitation_progress >= 10


def test_normal_sentence_clears_consecutive_rehab(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=8)
    engine = SimulationEngine(rng_seed=1)
    state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    state, _ = engine.submit_legal_choice(state, "E082_A", rules)
    state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    next_state, _ = engine.submit_legal_choice(state, "E082_B", rules)
    legal = LegalState.from_life_state_dict(next_state.legal)
    assert legal.consecutive_rehabilitation_years == 0


def test_serve_one_year_reduces_remaining(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=5)
    engine = SimulationEngine(rng_seed=1)
    state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    next_state, _ = engine.submit_legal_choice(state, "E082_B", rules)
    legal = LegalState.from_life_state_dict(next_state.legal)
    assert legal.sentence_remaining_years == 4
    assert legal.years_served == 1


def test_reduction_requires_minimum_years_served(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=10)
    engine = SimulationEngine(rng_seed=1)
    for _ in range(2):
        state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
        state, result = engine.submit_legal_choice(state, "E082_A", rules)
        assert "sentence_reduction_years" not in result


def test_mandatory_reduction_after_five_consecutive_years(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=10)
    engine = SimulationEngine(rng_seed=1)
    result: dict = {}
    for _ in range(5):
        state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
        state, result = engine.submit_legal_choice(state, "E082_A", rules)
    assert "sentence_reduction_years" in result


def test_reduction_ratio_at_or_below_120_progress(life_state, rules) -> None:
    legal = LegalState(
        is_in_prison=True,
        sentence_total_years=10,
        sentence_remaining_years=8,
        years_served=3,
        rehabilitation_progress=100,
        consecutive_rehabilitation_years=3,
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    context = make_context(state, rules)
    context.result_collector.bind_legal_context(state)
    outcome: dict = {}
    LegalService()._try_sentence_reduction(context, legal, rules["legal"], outcome)
    assert outcome["reduction_ratio"] == 0.2
    assert outcome["sentence_reduction_years"] == math.floor(10 * 0.2)


def test_reduction_ratio_above_120_progress(life_state, rules) -> None:
    legal = LegalState(
        is_in_prison=True,
        sentence_total_years=10,
        sentence_remaining_years=8,
        years_served=3,
        rehabilitation_progress=135,
        consecutive_rehabilitation_years=3,
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    context = make_context(state, rules)
    context.result_collector.bind_legal_context(state)
    outcome: dict = {}
    LegalService()._try_sentence_reduction(context, legal, rules["legal"], outcome)
    assert outcome["reduction_ratio"] == pytest.approx(0.35)
    assert outcome["sentence_reduction_years"] == math.floor(10 * 0.35)


def test_short_sentence_early_release_with_supervision(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=4)
    engine = SimulationEngine(rng_seed=1)
    for _ in range(3):
        state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
        state, result = engine.submit_legal_choice(state, "E082_A", rules)
    legal = LegalState.from_life_state_dict(state.legal)
    assert result.get("early_release") is True
    assert legal.is_in_prison is False
    assert legal.is_under_supervision is True
    assert legal.supervision_remaining_years == 1


def test_escape_success_probability_from_rules(rules) -> None:
    assert rules["legal"]["escape_success_probability"] == 0.05


def test_escape_failure_increases_sentence_by_20_percent(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=8)
    engine = SimulationEngine(rng_seed=1)
    state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    next_state, result = engine.submit_legal_choice(state, "E082_C", rules)
    legal = LegalState.from_life_state_dict(next_state.legal)
    assert result["escape"] == "failed"
    assert legal.sentence_remaining_years == 8 - 1 + math.ceil(8 * 0.2)


def test_escape_success_enters_fugitive_state(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=8, seed=31)
    engine = SimulationEngine(rng_seed=31)
    state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    next_state, result = engine.submit_legal_choice(state, "E082_C", rules)
    legal = LegalState.from_life_state_dict(next_state.legal)
    assert result["escape"] == "success"
    assert legal.is_fugitive is True
    assert legal.is_in_prison is False
    assert legal.education_locked is True


def test_fugitive_blocks_education_and_career(life_state, rules) -> None:
    legal = build_default_legal_state().model_copy(
        update={
            "is_fugitive": True,
            "education_locked": True,
            "career_locked": True,
            "normal_job_locked": True,
        }
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    context = make_context(state, rules)
    EducationService().run(context)
    CareerService().run(context)
    assert not context.event_bus.by_type(SimulationEventType.EDUCATION_STATE_UPDATE_REQUESTED)
    assert not context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)


def test_fugitive_year_returns_e089(life_state, rules) -> None:
    legal = build_default_legal_state().model_copy(
        update={"is_fugitive": True, "sentence_remaining_years": 5}
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    engine = SimulationEngine(rng_seed=1)
    _, year_result, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    assert year_result.pending_legal_event["event_id"] == "E089"


def test_fugitive_labor_publishes_asset_change(life_state, rules) -> None:
    legal = build_default_legal_state().model_copy(
        update={"is_fugitive": True, "sentence_remaining_years": 5}
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    state.pending_legal_event = {
        "event_id": "E089",
        "name": "潜逃打零工",
        "event_text": "t",
        "choices": [{"choice_id": "E089_A", "label": "a", "choice_text": "b"}],
    }
    engine = SimulationEngine(rng_seed=1)
    context_state = state
    context = make_context(context_state, rules)
    context.result_collector.bind_legal_context(context_state)
    LegalService().submit_choice(context, "E089_A")
    asset_events = context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)
    assert asset_events
    assert asset_events[0].payload["delta"] == rules["legal"]["fugitive_labor_income_low"]


def test_recapture_reimprisons_and_increases_sentence(life_state, rules) -> None:
    legal = build_default_legal_state().model_copy(
        update={"is_fugitive": True, "sentence_remaining_years": 10}
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    state.pending_legal_event = {
        "event_id": "E089",
        "name": "潜逃打零工",
        "event_text": "t",
        "choices": [{"choice_id": "E089_A", "label": "a", "choice_text": "b"}],
    }
    engine = SimulationEngine(rng_seed=1)
    next_state, result = engine.submit_legal_choice(state, "E089_A", rules)
    legal = LegalState.from_life_state_dict(next_state.legal)
    assert legal.is_in_prison is True
    assert legal.is_fugitive is False
    assert legal.sentence_remaining_years == 10 + math.ceil(10 * 0.3)
    assert result["event_id"] == "E089"


def test_formal_release_clears_prison_keeps_record(life_state, rules) -> None:
    state, _ = _imprison(_adult_state(life_state), rules, years=1)
    engine = SimulationEngine(rng_seed=1)
    state, _, _ = engine.advance_one_year(state, {"annual_focus": "balanced_year"}, rules)
    next_state, result = engine.submit_legal_choice(state, "E082_B", rules)
    legal = LegalState.from_life_state_dict(next_state.legal)
    assert result.get("released") is True
    assert legal.is_in_prison is False
    assert legal.has_criminal_record is True
    assert legal.civil_service_banned is True
    assert legal.research_job_ban_remaining_years == 10


def test_employment_penalty_rates_by_year(rules) -> None:
    legal = LegalState(has_criminal_record=True, post_release_employment_penalty_year=1)
    penalties = {
        1: 0.30,
        2: 0.24,
        3: 0.18,
        4: 0.12,
        5: 0.06,
        6: 0.0,
    }
    for year, expected in penalties.items():
        legal.post_release_employment_penalty_year = year
        assert legal.employment_penalty_rate(rules) == pytest.approx(expected)


def test_supervision_blocks_normal_career(life_state, rules) -> None:
    legal = build_default_legal_state().model_copy(
        update={
            "is_under_supervision": True,
            "supervision_remaining_years": 1,
            "normal_job_locked": True,
            "career_locked": True,
        }
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    context = make_context(state, rules)
    CareerService().run(context)
    assert not context.event_bus.by_type(SimulationEventType.ASSET_CHANGE_REQUESTED)


def test_supervision_end_unlocks_normal_job(life_state, rules) -> None:
    legal = build_default_legal_state().model_copy(
        update={
            "is_under_supervision": True,
            "supervision_remaining_years": 1,
            "normal_job_locked": True,
            "career_locked": True,
        }
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    context = make_context(state, rules)
    context.result_collector.bind_legal_context(state)
    LegalService().run(context)
    working = context.result_collector._legal_working
    assert working.is_under_supervision is False
    assert working.normal_job_locked is False


def test_legal_module_does_not_modify_assets_directly(life_state, rules) -> None:
    legal = build_default_legal_state().model_copy(
        update={"is_fugitive": True, "sentence_remaining_years": 4}
    )
    state = _adult_state(life_state.model_copy(update={"legal": legal.to_life_state_dict()}))
    before_cash = state.assets.get("cash", 0)
    state.pending_legal_event = {
        "event_id": "E089",
        "name": "x",
        "event_text": "t",
        "choices": [],
    }
    context = make_context(state, rules)
    context.result_collector.bind_legal_context(state)
    LegalService().submit_choice(context, "E089_A")
    assert context.state.assets.get("cash", 0) == before_cash


def test_escape_probability_uses_backend_rng() -> None:
    assert ServerRandom(31).random() <= 0.05
    assert ServerRandom(1).random() > 0.05

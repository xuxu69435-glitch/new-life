from app.application.game_command_service import GameCommandService
from app.engine.simulation_engine import SimulationEngine
from app.modules.narrative.composer import AnnualNarrativeComposer
from app.modules.narrative.models import AnnualNarrativeInput
from app.modules.narrative.service import NarrativeService

from conftest import make_context


def test_normal_year_generates_summary_text(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    _, result, _ = engine.advance_one_year(
        life_state,
        {"annual_focus": "balanced_year"},
        rules,
    )
    assert result.annual_summary_text
    assert result.narrative_result is not None
    assert result.narrative_result["summary_text"]
    assert result.narrative_text == result.annual_summary_text


def test_quiet_year_still_has_narrative(life_state, rules) -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=5,
            age_after=6,
            life_stage="childhood",
            major_flags={"has_notable_events": False},
        )
    )
    assert result.summary_text
    assert result.opening_text
    assert result.closing_text


def test_random_event_in_narrative(life_state, rules) -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=20,
            age_after=21,
            life_stage="adult",
            triggered_random_events=[
                {
                    "event_id": "E001",
                    "name": "测试事件",
                    "narrative_text": "一件意外的事情发生了。",
                }
            ],
            major_flags={"has_notable_events": True},
        )
    )
    assert any(
        "随机事件" in text
        for text in result.summary_text.split("\n")
        + result.major_event_texts
        + [event["text"] for event in result.priority_events]
    )
    section_ids = [section.section_id for section in result.display_sections]
    assert "major_events" in section_ids or "overview" in section_ids


def test_education_section_in_narrative() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=11,
            age_after=12,
            life_stage="childhood",
            education_changes={
                "stage_before": "primary_school",
                "stage_after": "middle_school",
                "graduated": True,
            },
            major_flags={"has_notable_events": True},
        )
    )
    education_section = next(
        (s for s in result.display_sections if s.section_id == "education"),
        None,
    )
    assert education_section is not None
    assert "学业" in education_section.content or "毕业" in education_section.content


def test_career_income_section() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=24,
            age_after=25,
            life_stage="adult",
            career_changes={
                "status_before": "unemployed",
                "status_after": "employed",
                "career_path": "office_worker",
                "career_income_change": 18000,
            },
            asset_changes={"cash": 18000},
            major_flags={"has_notable_events": True},
        )
    )
    career_section = next(
        (s for s in result.display_sections if s.section_id == "career_assets"),
        None,
    )
    assert career_section is not None
    assert "收入" in career_section.content or "资产" in career_section.content


def test_marriage_highlighted_in_narrative() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=28,
            age_after=29,
            life_stage="adult",
            married_this_year=True,
            relationship_status_before="dating",
            relationship_status_after="married",
            major_flags={"has_notable_events": True},
        )
    )
    assert any("婚姻" in text for text in result.major_event_texts)
    family_section = next((s for s in result.display_sections if s.section_id == "family"), None)
    assert family_section is not None


def test_childbirth_highlighted() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=30,
            age_after=31,
            life_stage="adult",
            child_born_this_year=True,
            major_flags={"has_notable_events": True},
        )
    )
    assert any("新生命" in text or "父母" in text for text in result.major_event_texts)


def test_health_section_in_narrative() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=40,
            age_after=41,
            life_stage="adult",
            health_changes={
                "health_score_before": 70,
                "health_score_after": 60,
                "health_score_delta": -10,
                "warnings": ["体能下降"],
            },
            major_flags={"has_notable_events": True},
        )
    )
    health_section = next((s for s in result.display_sections if s.section_id == "health"), None)
    assert health_section is not None


def test_prison_year_legal_centered() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=30,
            age_after=31,
            life_stage="adult",
            legal_changes={"is_in_prison": True, "sentence_remaining_years": 5},
            pending_legal_event={"event_id": "E082", "name": "年度服刑选择"},
            major_flags={"has_notable_events": True},
        )
    )
    assert "服刑" in result.opening_text
    legal_section = next((s for s in result.display_sections if s.section_id == "legal"), None)
    assert legal_section is not None


def test_fugitive_year_narrative() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=30,
            age_after=31,
            life_stage="adult",
            legal_changes={"is_fugitive": True, "last_legal_event": "E088"},
            major_flags={"has_notable_events": True},
        )
    )
    assert "潜逃" in result.opening_text or "正常社会" in result.opening_text


def test_release_narrative() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=35,
            age_after=36,
            life_stage="adult",
            legal_before={"is_in_prison": True},
            legal_changes={"is_in_prison": False, "last_legal_event": "E091"},
            major_flags={"has_notable_events": True},
        )
    )
    assert any("出狱" in text or "社会" in text for text in result.major_event_texts)


def test_mainline_completion_in_narrative() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=2,
            age_after=3,
            life_stage="infant",
            completed_tasks_this_year=["M001"],
            mainline_narrative=["你健康地度过了婴幼儿阶段。"],
            major_flags={"has_notable_events": True},
        )
    )
    mainline_section = next((s for s in result.display_sections if s.section_id == "mainline"), None)
    assert mainline_section is not None
    assert "M001" in mainline_section.content or "主线" in mainline_section.content


def test_death_year_highest_priority() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=70,
            age_after=71,
            life_stage="elder",
            is_dead=True,
            death_type="natural_death",
            death_reason="natural causes",
            married_this_year=True,
            major_flags={"has_notable_events": True},
        )
    )
    assert result.priority_events[0]["type"] == "death"
    assert result.tone == "solemn"
    assert "离开了人世" in result.summary_text or "句号" in result.summary_text


def test_inheritance_after_death() -> None:
    composer = AnnualNarrativeComposer()
    result = composer.compose(
        AnnualNarrativeInput(
            life_id="life-1",
            age_before=70,
            age_after=71,
            life_stage="elder",
            is_dead=True,
            death_type="natural_death",
            inheritance_result={
                "status": "settled",
                "gross_estate": 100000,
                "net_estate": 80000,
            },
            major_flags={"has_notable_events": True},
        )
    )
    assert any(event["type"] == "inheritance" for event in result.priority_events)
    assert any("遗产" in text for text in result.major_event_texts)


def test_year_result_returns_narrative_result(life_state, rules) -> None:
    engine = SimulationEngine(rng_seed=1)
    _, result, _ = engine.advance_one_year(
        life_state,
        {"annual_focus": "balanced_year"},
        rules,
    )
    assert result.narrative_result is not None
    assert result.display_sections
    assert isinstance(result.major_event_texts, list)


def test_narrative_service_does_not_modify_state(life_state, rules) -> None:
    before = life_state.model_copy(deep=True)
    context = make_context(life_state, rules)
    context.result_collector.bind_family_context(life_state, rules)
    context.result_collector.bind_legal_context(life_state)
    context.result_collector.bind_mainline_context(life_state)
    NarrativeService().run(context)
    assert context.state.model_dump() == before.model_dump()


def test_create_life_narrative_rules_load(rules) -> None:
    assert rules["narrative"]["use_narrative_v1"] is True

from uuid import uuid4

import pytest

from app.application.game_command_service import GameCommandService
from app.application.save_migration_service import SaveMigrationService
from app.application.save_service import SaveService
from app.engine.simulation_context import LifeState, SimulationEventType, YearResult
from app.infrastructure.rng import ServerRandom
from app.modules.legal.models import LegalState
from app.modules.random_events.condition_matcher import RandomEventConditionMatcher
from app.modules.random_events.choice_effect_resolver import RandomEventChoiceEffectResolver
from app.modules.random_events.library_models import V1EventChoice, V1EventDefinition, AgeRange
from app.modules.romance.constants import ROMANCE_EFFECT_TYPES
from app.modules.romance.events import RomanceEventProcessor
from app.modules.romance.models import RomanticCandidate, RomanticRelationship, RomanceState, clamp_score
from app.modules.romance.processor import RomanceAnnualProcessor
from app.modules.romance.rules import build_default_romance_state, get_romance_rules
from app.modules.romance.service import RomanceService
from app.modules.romance.summary import build_romance_narrative_lines
from app.modules.social.models import SocialPerson, SocialRelationship, SocialState
from app.modules.timeline.generator import TimelineGenerator
from app.modules.timeline.models import LifeYearSnapshot
from tests.conftest import make_context


def _romance_rules_high_chance(rules: dict) -> dict:
    patched = dict(rules)
    romance = dict(get_romance_rules(rules))
    romance["school_crush_chance"] = 1.0
    romance["university_romance_chance"] = 1.0
    romance["workplace_romance_chance"] = 1.0
    romance["candidate_from_social_chance"] = 1.0
    romance["friend_to_candidate_chance"] = 1.0
    patched["romance"] = romance
    return patched


def test_create_life_has_stable_romance_state(rules) -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    romance = RomanceState.from_life_state_dict(state.romance)
    assert romance.candidates == []
    assert romance.romance_summary


def test_legacy_state_migration_adds_romance(rules) -> None:
    legacy = {
        "life_id": str(uuid4()),
        "person_id": str(uuid4()),
        "age": 10,
        "life_stage": "childhood",
        "attributes": dict(rules["default_attributes"]),
        "health": dict(rules["default_health"]),
        "family": {},
        "education": {},
        "career": {},
        "assets": dict(rules["default_assets"]),
        "flags": {},
        "rule_version": "v1",
    }
    migrated = SaveMigrationService().ensure_life_state_shape(LifeState.model_validate(legacy), rules)
    assert migrated.romance
    assert "candidates" in migrated.romance


def test_romantic_candidate_and_relationship_fields() -> None:
    candidate = RomanticCandidate(candidate_id="c1", name="测试", favor=120, trust=-5).clamp_values()
    relationship = RomanticRelationship(
        relationship_id="r1",
        candidate_id="c1",
        partner_name="恋人",
        favor=200,
        intimacy=-10,
        stability=300,
    ).clamp_values()
    assert candidate.favor == 100
    assert candidate.trust == 0
    assert relationship.favor == 100
    assert relationship.intimacy == 0
    assert relationship.stability == 100


def test_under_14_no_candidates(rules, life_state) -> None:
    romance = build_default_romance_state(rules)
    life_state.age = 12
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(1))
    romance = processor.apply_annual_changes(romance, life_state, _romance_rules_high_chance(rules))
    assert not romance.new_candidates_this_year


def test_teen_only_crush_or_ambiguous(rules, life_state) -> None:
    romance = build_default_romance_state(rules)
    life_state.age = 15
    life_state.life_stage = "teen"
    life_state.education = {**life_state.education, "current_stage": "middle", "is_enrolled": True}
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(2))
    romance = processor.apply_annual_changes(romance, life_state, _romance_rules_high_chance(rules))
    assert romance.new_candidates_this_year
    for candidate in romance.get_candidate_models().values():
        assert candidate.status in {"crush", "ambiguous"}
        assert romance.get_current_relationship() is None or romance.get_current_relationship().status != "dating"


def test_adult_can_generate_candidates(rules, life_state) -> None:
    romance = build_default_romance_state(rules)
    life_state.age = 20
    life_state.life_stage = "adult"
    life_state.education = {**life_state.education, "current_stage": "college", "is_enrolled": True}
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(3))
    romance = processor.apply_annual_changes(romance, life_state, _romance_rules_high_chance(rules))
    assert romance.new_candidates_this_year


def test_prison_blocks_new_candidates(rules, life_state) -> None:
    romance = build_default_romance_state(rules)
    life_state.age = 20
    life_state.legal = LegalState(is_in_prison=True).to_life_state_dict()
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(1))
    romance = processor.apply_restricted_decay(romance, life_state.age + 1, rules, mode="prison")
    assert not romance.new_candidates_this_year


def test_fugitive_blocks_new_candidates(rules, life_state) -> None:
    romance = build_default_romance_state(rules)
    life_state.age = 22
    life_state.career = {**life_state.career, "employment_status": "employed"}
    life_state.legal = LegalState(is_fugitive=True).to_life_state_dict()
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(1))
    romance = processor.apply_restricted_decay(romance, life_state.age + 1, rules, mode="fugitive")
    assert not romance.new_candidates_this_year


def test_social_romantic_candidate_import(rules, life_state) -> None:
    romance = build_default_romance_state(rules)
    life_state.age = 18
    life_state.social = SocialState(
        persons=[SocialPerson(person_id="p1", name="心动对象", role="romantic_candidate").to_dict()],
        relationships=[
            SocialRelationship(
                relationship_id="sr1",
                person_id="p1",
                relationship_type="romantic_candidate",
                closeness=70,
                trust=60,
            ).to_dict()
        ],
    ).to_life_state_dict()
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(4))
    romance = processor.apply_annual_changes(romance, life_state, _romance_rules_high_chance(rules))
    assert romance.new_candidates_this_year


def test_friend_can_convert_to_candidate(rules, life_state) -> None:
    romance = build_default_romance_state(rules)
    life_state.age = 19
    life_state.social = SocialState(
        persons=[SocialPerson(person_id="p1", name="好友", role="friend").to_dict()],
        relationships=[
            SocialRelationship(
                relationship_id="sr1",
                person_id="p1",
                relationship_type="friend",
                closeness=75,
                trust=60,
                conflict=10,
            ).to_dict()
        ],
    ).to_life_state_dict()
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(6))
    romance = processor.apply_annual_changes(romance, life_state, _romance_rules_high_chance(rules))
    assert romance.new_candidates_this_year


def test_dating_blocks_new_candidates(rules, life_state) -> None:
    romance = RomanceState(
        current_relationship=RomanticRelationship(
            relationship_id="rr1",
            candidate_id="c1",
            partner_name="恋人",
            status="dating",
            favor=70,
            trust=60,
            intimacy=55,
        ).to_dict(),
        candidates=[RomanticCandidate(candidate_id="c1", name="恋人", status="inactive").to_dict()],
    )
    life_state.age = 22
    life_state.career = {**life_state.career, "employment_status": "employed"}
    processor = RomanceAnnualProcessor(get_romance_rules(_romance_rules_high_chance(rules)), ServerRandom(1))
    romance = processor.apply_annual_changes(romance, life_state, _romance_rules_high_chance(rules))
    assert not romance.new_candidates_this_year


def test_relationship_can_start_dating(rules, life_state) -> None:
    romance = RomanceState(
        candidates=[
            RomanticCandidate(
                candidate_id="c1",
                name="候选人",
                status="candidate",
                favor=70,
                trust=50,
                attraction=55,
            ).to_dict()
        ]
    )
    life_state.age = 19
    processor = RomanceAnnualProcessor(get_romance_rules(rules), ServerRandom(1))
    romance = processor.apply_annual_changes(romance, life_state, rules)
    assert romance.get_current_relationship() is not None
    assert romance.get_current_relationship().status == "dating"


def test_high_conflict_cooling_off_or_breakup(rules) -> None:
    romance = RomanceState(
        current_relationship=RomanticRelationship(
            relationship_id="rr1",
            candidate_id="c1",
            partner_name="恋人",
            status="dating",
            favor=50,
            trust=40,
            intimacy=40,
            conflict=76,
            stability=30,
        ).to_dict(),
    )
    processor = RomanceAnnualProcessor(get_romance_rules(rules), ServerRandom(1))
    processor._advance_current_relationship(romance, 25, rules, decay_multiplier=1)
    rel = romance.get_current_relationship()
    assert rel.status in {"cooling_off", "broken_up"}


def test_stable_relationship_engagement_intent(rules) -> None:
    romance = RomanceState(
        current_relationship=RomanticRelationship(
            relationship_id="rr1",
            candidate_id="c1",
            partner_name="恋人",
            status="dating",
            favor=80,
            trust=75,
            intimacy=78,
            conflict=10,
            stability=80,
        ).to_dict(),
    )
    processor = RomanceAnnualProcessor(get_romance_rules(rules), ServerRandom(1))
    processor._advance_current_relationship(romance, 25, rules, decay_multiplier=1)
    rel = romance.get_current_relationship()
    assert rel.status == "engagement_intent"
    assert romance.romance_flags.get("marriage_candidate_signal")


def test_romance_effect_types_reserved() -> None:
    assert "romance_candidate_created" in ROMANCE_EFFECT_TYPES
    assert "romance_relationship_started" in ROMANCE_EFFECT_TYPES


def test_choice_effect_resolver_romance_effect() -> None:
    resolver = RandomEventChoiceEffectResolver()
    event = V1EventDefinition(event_id="TEST", name="test", category="social", event_text="", choices=[])
    choice = V1EventChoice(
        choice_id="T_A",
        label="A",
        choice_text="A",
        effects_text="create candidate",
        effects=[{"type": "romance_candidate_created", "name": "心动对象", "status": "crush"}],
    )
    resolved = resolver.resolve_choice(event, choice, None)  # type: ignore[arg-type]
    assert resolved[0][0] == SimulationEventType.ROMANCE_CANDIDATE_CREATED


def test_condition_matcher_is_dating(rules, life_state) -> None:
    life_state.romance = RomanceState(
        current_relationship=RomanticRelationship(
            relationship_id="rr1",
            candidate_id="c1",
            partner_name="恋人",
            status="dating",
        ).to_dict()
    ).to_life_state_dict()
    event = V1EventDefinition(
        event_id="TEST",
        name="test",
        category="social",
        conditions={"is_dating": True},
        event_text="",
        choices=[],
    )
    assert RandomEventConditionMatcher().matches(event, life_state)


def test_year_result_includes_romance_changes(rules) -> None:
    service = GameCommandService()
    state, _ = service.create_life()
    patched = _romance_rules_high_chance(rules)
    state.age = 19
    state.life_stage = "adult"
    state.education = {**state.education, "current_stage": "college", "is_enrolled": True}
    next_state, result, _ = service.engine.advance_one_year(
        state,
        {"annual_focus": "balanced_year"},
        patched,
    )
    assert next_state.romance
    assert result.romance_changes or result.romance_narrative or result.new_romantic_candidates is not None


def test_narrative_consumes_romance_changes() -> None:
    romance = RomanceState(
        new_candidates_this_year=["c1"],
        candidates=[RomanticCandidate(candidate_id="c1", name="苏晴", status="crush").to_dict()],
        romance_changes_this_year=[{"change_type": "relationship_started", "partner_name": "苏晴"}],
        current_relationship=RomanticRelationship(
            relationship_id="rr1",
            candidate_id="c1",
            partner_name="苏晴",
            status="dating",
        ).to_dict(),
    )
    lines = build_romance_narrative_lines(romance)
    assert lines


def test_timeline_generates_romance_entry() -> None:
    result = YearResult(
        life_id="life-1",
        age_before=20,
        age_after=21,
        is_dead=False,
        new_romantic_candidates=[{"name": "苏晴", "status": "crush"}],
        current_romantic_relationship={"partner_name": "苏晴", "status": "dating"},
    )
    snapshot = LifeYearSnapshot(
        snapshot_id="snap-1",
        life_id="life-1",
        age_before=20,
        age_after=21,
        year_index=21,
        rule_version="v1",
        state_before={"age": 20},
        state_after={"age": 21},
        year_result={},
    )
    entries = TimelineGenerator().generate(result, snapshot)
    assert any(item.entry_type == "romance" for item in entries)


def test_sqlite_persists_romance_state(rules, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SAVE_REPOSITORY_TYPE", "sqlite")
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(tmp_path / "romance.sqlite3"))
    from app.infrastructure.config import get_settings
    from app.infrastructure.save.factory import create_save_repository
    from app.infrastructure.save.sqlite_db import clear_sqlite_caches

    get_settings.cache_clear()
    clear_sqlite_caches()
    repo = create_save_repository()
    service = SaveService(repository=repo)
    state = service.create_life("v1", rules)
    romance = RomanceState.from_life_state_dict(state.romance)
    romance = RomanceEventProcessor().process(
        SimulationEventType.ROMANCE_CANDIDATE_CREATED,
        {"name": "存档恋人", "status": "crush", "favor": 60},
        romance,
        state.age,
    )
    state.romance = romance.to_life_state_dict()
    service.save_life_state(state, rules=rules)
    loaded = service.get_life_state(state.life_id, rules=rules)
    assert loaded.romance.get("candidates")


def test_death_does_not_advance_romance(rules, life_state) -> None:
    life_state.is_dead = True
    context = make_context(life_state, rules)
    context.result_collector.bind_romance_context(life_state)
    RomanceService().run(context)
    assert context.event_bus.all() == []

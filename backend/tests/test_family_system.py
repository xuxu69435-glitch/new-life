import copy
from uuid import uuid4

import pytest

from app.application.save_service import SaveService
from app.engine.simulation_engine import SimulationEngine
from app.modules.family.models import FamilyMember, FamilyState
from app.modules.family.rules import build_default_family_state
from app.modules.inheritance.rules import settle_estate
from app.modules.assets.models import AssetState
from app.modules.random_events.condition_matcher import RandomEventConditionMatcher
from app.modules.random_events.v1_draw import RandomEventV1DrawService
from app.rules.random_event_library_loader import RandomEventLibraryLoader


def _family_dict(**overrides) -> dict:
    state = build_default_family_state({"family": {}})
    data = state.to_life_state_dict()
    data.update(overrides)
    return data


def _adult_life_state(rules, **family_overrides):
    from app.engine.simulation_context import LifeState
    from app.modules.education.rules import build_default_education_state
    from app.modules.career.rules import build_default_career_state

    family = _family_dict(**family_overrides)
    return LifeState(
        life_id="life-family",
        person_id="person-family",
        age=28,
        life_stage="adult",
        attributes=dict(rules["default_attributes"]),
        health=dict(rules["default_health"]),
        family=family,
        education=build_default_education_state(rules).to_life_state_dict(),
        career=build_default_career_state(rules).to_life_state_dict(),
        assets={"cash": 100000.0, "property_value": 0.0, "debt": 0.0, "net_worth": 100000.0, "asset_transactions": []},
        rule_version=rules["version"],
    )


@pytest.fixture
def v1_library():
    return RandomEventLibraryLoader().load()


def test_create_life_has_stable_family_state(rules) -> None:
    state = SaveService().create_life("v1", rules)
    family = FamilyState.from_life_state_dict(state.family)
    assert family.parents
    assert family.relationship_status == "single"
    assert 0 <= family.family_pressure <= 100
    assert 0 <= family.parent_child_relation <= 100
    assert family.family_tree_id


def test_family_state_compatible_with_inheritance(rules) -> None:
    family = FamilyState(
        parents=[],
        spouse=FamilyMember(person_id="spouse-1", name="Spouse", relation="spouse"),
        children=[
            FamilyMember(person_id="child-1", name="Child", relation="child", playable=True)
        ],
        generation=1,
        family_tree_id="tree-1",
        relationship_status="married",
    )
    assets = AssetState(cash=100000.0, property_value=0.0, debt=0.0)
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"])
    assert result.heirs
    assert result.net_estate > 0


def test_v1_family_events_upgraded_to_active(v1_library) -> None:
    active_ids = {f"E{i:02d}" if i < 100 else f"E{i:03d}" for i in range(4, 8)}
    active_ids.update({f"E0{i}" for i in range(51, 59)})
    for event_id in ["E004", "E007", "E051", "E052", "E053", "E054", "E055", "E056", "E057", "E058"]:
        event = v1_library.by_id()[event_id]
        assert event.implementation_status == "active", event_id


def test_e051_drawable_when_single(life_state, rules, v1_library) -> None:
    life_state.age = 25
    life_state.life_stage = "adult"
    life_state.family = _family_dict(relationship_status="single")
    life_state.attributes["charm"] = 50
    event = v1_library.by_id()["E051"]
    assert RandomEventConditionMatcher().matches(event, life_state)
    pool = RandomEventV1DrawService().eligible_normal_events([event], life_state, {})
    assert pool == [event]


def test_e052_only_dating(life_state, rules, v1_library) -> None:
    event = v1_library.by_id()["E052"]
    matcher = RandomEventConditionMatcher()
    life_state.age = 25
    life_state.life_stage = "adult"
    life_state.family = _family_dict(relationship_status="single", partner_relation=70)
    assert matcher.matches(event, life_state) is False
    life_state.family = _family_dict(relationship_status="dating", partner_relation=65)
    assert matcher.matches(event, life_state) is True


def test_e054_only_dating_with_relation(life_state, rules, v1_library) -> None:
    event = v1_library.by_id()["E054"]
    matcher = RandomEventConditionMatcher()
    life_state.age = 28
    life_state.life_stage = "adult"
    life_state.family = _family_dict(relationship_status="dating", partner_relation=60)
    assert matcher.matches(event, life_state) is False
    life_state.family = _family_dict(relationship_status="dating", partner_relation=75)
    assert matcher.matches(event, life_state) is True


def test_e055_only_married(life_state, rules, v1_library) -> None:
    event = v1_library.by_id()["E055"]
    matcher = RandomEventConditionMatcher()
    life_state.age = 30
    life_state.life_stage = "adult"
    life_state.health["health_score"] = 80
    life_state.family = _family_dict(relationship_status="dating")
    assert matcher.matches(event, life_state) is False
    life_state.family = _family_dict(
        relationship_status="married",
        spouse=FamilyMember(person_id="s1", name="Spouse", relation="spouse").model_dump(),
    )
    assert matcher.matches(event, life_state) is True


def test_e056_requires_children(life_state, rules, v1_library) -> None:
    event = v1_library.by_id()["E056"]
    matcher = RandomEventConditionMatcher()
    life_state.age = 35
    life_state.life_stage = "adult"
    life_state.family = _family_dict(children_count=0, children=[])
    assert matcher.matches(event, life_state) is False
    life_state.family = _family_dict(
        children_count=1,
        children=[FamilyMember(person_id="c1", name="Kid", relation="child", age=10).model_dump()],
    )
    assert matcher.matches(event, life_state) is True


def test_e058_married_low_partner_relation(life_state, rules, v1_library) -> None:
    event = v1_library.by_id()["E058"]
    matcher = RandomEventConditionMatcher()
    life_state.age = 40
    life_state.life_stage = "adult"
    life_state.family = _family_dict(relationship_status="married", partner_relation=50)
    assert matcher.matches(event, life_state) is False
    life_state.family = _family_dict(
        relationship_status="married",
        partner_relation=30,
        spouse=FamilyMember(person_id="s1", name="Spouse", relation="spouse").model_dump(),
    )
    assert matcher.matches(event, life_state) is True


def test_e051_choice_enters_dating(rules) -> None:
    state = _adult_life_state(rules, relationship_status="single")
    state.pending_random_event = {
        "event_id": "E051",
        "name": "遇到心动的人",
        "category": "relationship_family",
        "event_text": "test",
        "choices": [],
        "year_age": 28,
        "pool_type": "normal",
    }
    engine = SimulationEngine(rng_seed=1)
    next_state, _ = engine.submit_random_event_choice(state, "E051_A", rules)
    family = FamilyState.from_life_state_dict(next_state.family)
    assert family.relationship_status == "dating"
    assert family.dating_partner is not None


def test_e054_marriage_updates_family_and_assets(rules) -> None:
    state = _adult_life_state(
        rules,
        relationship_status="dating",
        partner_relation=75,
        dating_partner=FamilyMember(person_id="p1", name="Partner", relation="partner").model_dump(),
    )
    cash_before = float(state.assets["cash"])
    state.pending_random_event = {"event_id": "E054", "name": "结婚选择", "category": "x", "event_text": "t", "choices": [], "year_age": 28, "pool_type": "normal"}
    engine = SimulationEngine(rng_seed=1)
    next_state, _ = engine.submit_random_event_choice(state, "E054_A", rules)
    family = FamilyState.from_life_state_dict(next_state.family)
    assert family.relationship_status == "married"
    assert family.spouse is not None
    assert float(next_state.assets["cash"]) == cash_before - 20000


def test_e055_child_increases_children(rules) -> None:
    state = _adult_life_state(
        rules,
        relationship_status="married",
        spouse=FamilyMember(person_id="s1", name="Spouse", relation="spouse").model_dump(),
    )
    state.pending_random_event = {"event_id": "E055", "name": "生育选择", "category": "x", "event_text": "t", "choices": [], "year_age": 28, "pool_type": "normal"}
    engine = SimulationEngine(rng_seed=1)
    next_state, _ = engine.submit_random_event_choice(state, "E055_A", rules)
    family = FamilyState.from_life_state_dict(next_state.family)
    assert family.children_count == 1
    assert len(family.children) == 1


def test_e056_high_education_reduces_assets(rules) -> None:
    state = _adult_life_state(
        rules,
        children_count=1,
        children=[FamilyMember(person_id="c1", name="Kid", relation="child", age=12).model_dump()],
    )
    cash_before = float(state.assets["cash"])
    state.pending_random_event = {"event_id": "E056", "name": "子女教育支出", "category": "x", "event_text": "t", "choices": [], "year_age": 35, "pool_type": "normal"}
    engine = SimulationEngine(rng_seed=1)
    next_state, _ = engine.submit_random_event_choice(state, "E056_A", rules)
    assert float(next_state.assets["cash"]) == cash_before - 15000


def test_e058_divorce_changes_status(rules) -> None:
    state = _adult_life_state(
        rules,
        relationship_status="married",
        partner_relation=30,
        spouse=FamilyMember(person_id="s1", name="Spouse", relation="spouse").model_dump(),
    )
    state.pending_random_event = {"event_id": "E058", "name": "离婚危机", "category": "x", "event_text": "t", "choices": [], "year_age": 40, "pool_type": "normal"}
    engine = SimulationEngine(rng_seed=1)
    next_state, _ = engine.submit_random_event_choice(state, "E058_B", rules)
    family = FamilyState.from_life_state_dict(next_state.family)
    assert family.relationship_status == "divorced"
    assert family.spouse is None


def test_planned_events_still_not_drawable(v1_library, life_state) -> None:
    planned = [e for e in v1_library.events if e.implementation_status == "planned"]
    draw = RandomEventV1DrawService()
    life_state.age = 30
    life_state.life_stage = "adult"
    assert draw.eligible_normal_events(planned, life_state, {}) == []


def test_inheritance_reads_spouse_and_children_after_family_changes(rules) -> None:
    state = _adult_life_state(
        rules,
        relationship_status="married",
        spouse=FamilyMember(person_id="s1", name="Spouse", relation="spouse").model_dump(),
        children_count=1,
        children=[FamilyMember(person_id="c1", name="Kid", relation="child", playable=True, age=5).model_dump()],
    )
    family = FamilyState.from_life_state_dict(state.family)
    assets = AssetState.from_life_state_dict(state.assets, rules)
    result = settle_estate(state.life_id, state.person_id, assets, family, rules["inheritance"])
    assert family.has_spouse()
    assert family.has_children()
    assert result.distribution

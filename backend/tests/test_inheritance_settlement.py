from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from app.application.game_command_service import GameCommandService, HeirContinuationError
from app.engine.simulation_context import SimulationEventType
from app.engine.simulation_engine import SimulationEngine
from app.modules.death.service import DeathService
from app.modules.inheritance.rules import settle_estate
from app.modules.inheritance.service import InheritanceService
from app.modules.assets.models import AssetState
from app.modules.family.models import FamilyMember, FamilyState

from conftest import make_context


def _family_with_spouse_only(spouse_id: str = "spouse-1") -> dict:
    return FamilyState(
        spouse=FamilyMember(person_id=spouse_id, name="Partner", relation="spouse"),
        generation=1,
        family_tree_id="tree-1",
    ).to_life_state_dict()


def _family_with_children_only() -> dict:
    return FamilyState(
        children=[
            FamilyMember(person_id="child-1", name="Child A", relation="child", playable=True),
            FamilyMember(person_id="child-2", name="Child B", relation="child", playable=True),
        ],
        generation=1,
        family_tree_id="tree-1",
    ).to_life_state_dict()


def _family_with_spouse_and_children() -> dict:
    return FamilyState(
        spouse=FamilyMember(person_id="spouse-1", name="Partner", relation="spouse"),
        children=[
            FamilyMember(person_id="child-1", name="Child A", relation="child", playable=True),
            FamilyMember(person_id="child-2", name="Child B", relation="child", playable=True),
        ],
        generation=1,
        family_tree_id="tree-1",
    ).to_life_state_dict()


def _run_inheritance(context) -> dict:
    InheritanceService().run(context)
    assert context.result_collector.inheritance_result is not None
    return context.result_collector.inheritance_result


def test_inheritance_module_does_not_run_without_death(life_state, rules) -> None:
    context = make_context(life_state, rules)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})

    InheritanceService().run(context)

    assert context.result_collector.inheritance_result is None


def test_inheritance_module_runs_after_death_confirmed(life_state, rules) -> None:
    context = make_context(life_state, rules)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})
    context.result_collector.confirm_death("test death", death_type="natural_death")

    result = _run_inheritance(context)

    assert result["status"] in {"settled", "zero_estate", "unclaimed"}
    assert result["tax_rate"] == pytest.approx(0.2)


def test_tax_amount_is_twenty_percent_of_gross_estate(rules) -> None:
    assets = AssetState(cash=10000.0, property_value=0.0, debt=0.0)
    family = FamilyState.from_life_state_dict(_family_with_spouse_only())
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"], "natural_death")

    assert result.gross_estate == pytest.approx(10000.0)
    assert result.tax_amount == pytest.approx(2000.0)
    assert result.net_estate == pytest.approx(8000.0)


def test_only_spouse_receives_all_net_estate(rules) -> None:
    assets = AssetState(cash=5000.0)
    family = FamilyState.from_life_state_dict(_family_with_spouse_only())
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"])

    assert len(result.heirs) == 1
    assert result.heirs[0].person_id == "spouse-1"
    assert result.heirs[0].amount == pytest.approx(4000.0)
    assert result.heirs[0].share_ratio == pytest.approx(1.0)


def test_only_children_split_net_estate_equally(rules) -> None:
    assets = AssetState(cash=6000.0)
    family = FamilyState.from_life_state_dict(_family_with_children_only())
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"])

    assert len(result.heirs) == 2
    assert result.heirs[0].amount == pytest.approx(2400.0)
    assert result.heirs[1].amount == pytest.approx(2400.0)


def test_spouse_and_children_share_by_rule_ratios(rules) -> None:
    assets = AssetState(cash=10000.0)
    family = FamilyState.from_life_state_dict(_family_with_spouse_and_children())
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"])

    assert result.heirs[0].person_id == "spouse-1"
    assert result.heirs[0].amount == pytest.approx(3200.0)
    assert result.heirs[1].amount == pytest.approx(2400.0)
    assert result.heirs[2].amount == pytest.approx(2400.0)


def test_no_heirs_returns_unclaimed_status(rules) -> None:
    assets = AssetState(cash=3000.0)
    family = FamilyState(generation=1, family_tree_id="tree-1")
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"])

    assert result.status == "unclaimed"
    assert result.unclaimed_amount == pytest.approx(2400.0)
    assert result.heirs == []


def test_debt_reduces_gross_estate(rules) -> None:
    assets = AssetState(cash=10000.0, debt=2000.0)
    family = FamilyState.from_life_state_dict(_family_with_spouse_only())
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"])

    assert result.gross_estate == pytest.approx(8000.0)
    assert result.tax_amount == pytest.approx(1600.0)


def test_negative_net_worth_returns_zero_estate(rules) -> None:
    assets = AssetState(cash=1000.0, debt=5000.0)
    family = FamilyState.from_life_state_dict(_family_with_spouse_only())
    result = settle_estate("life-1", "person-1", assets, family, rules["inheritance"])

    assert result.status == "zero_estate"
    assert result.gross_estate == 0.0
    assert result.net_estate == 0.0
    assert result.heirs == []


def test_inheritance_result_written_to_year_result(life_state, rules) -> None:
    state = life_state.model_copy(
        update={
            "assets": {"cash": 10000.0, "property_value": 0.0, "debt": 0.0, "net_worth": 10000.0},
            "family": _family_with_spouse_only(),
        }
    )
    engine = SimulationEngine(rng_seed=1)
    context = make_context(state, rules, seed=1)
    context.rng.random = MagicMock(return_value=0.0)
    context.event_bus.publish(
        SimulationEventType.DIRECT_DEATH_CANDIDATE_CREATED,
        "random_events",
        {"reason": "accident", "death_type": "direct_death", "probability": 1.0},
    )
    DeathService().run(context)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})
    InheritanceService().run(context)
    context.result_collector.collect_from_events(context.event_bus.all())
    next_state = context.result_collector.apply_to_state(state, rules)
    year_result = context.result_collector.to_year_result(state, next_state, context.event_bus.all(), [])

    assert year_result.inheritance_result is not None
    assert year_result.inheritance_result["tax_rate"] == pytest.approx(0.2)


def test_inheritance_module_does_not_confirm_death(life_state, rules) -> None:
    context = make_context(life_state, rules)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})
    context.result_collector.confirm_death("already dead", death_type="natural_death")

    InheritanceService().run(context)

    assert InheritanceService.can_confirm_death is False


def test_natural_and_direct_death_both_trigger_settlement(life_state, rules) -> None:
    for death_type in ("natural_death", "direct_death"):
        context = make_context(life_state, rules)
        context.result_collector.confirm_death("death", death_type=death_type)
        context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})
        result = _run_inheritance(context)
        assert result["created_from_death_type"] == death_type


def test_playable_heirs_endpoint_returns_descendants(life_state, rules) -> None:
    service = GameCommandService()
    state = life_state.model_copy(
        update={
            "is_dead": True,
            "death_reason": "test",
            "assets": {"cash": 10000.0, "property_value": 0.0, "debt": 0.0, "net_worth": 10000.0},
            "family": _family_with_children_only(),
        }
    )
    service.save_service.save_life_state(state)
    service.save_service.save_inheritance(
        state.life_id,
        settle_estate(
            state.life_id,
            state.person_id,
            AssetState.from_life_state_dict(state.assets),
            FamilyState.from_life_state_dict(state.family),
            rules["inheritance"],
            "natural_death",
        ).model_dump(),
    )

    payload = service.get_playable_heirs(state.life_id)

    assert payload["status"] == "available"
    assert len(payload["playable_heirs"]) == 2


def test_continue_as_heir_creates_new_life_skeleton(life_state, rules) -> None:
    service = GameCommandService()
    state = life_state.model_copy(
        update={
            "is_dead": True,
            "death_reason": "test",
            "assets": {"cash": 10000.0, "property_value": 0.0, "debt": 0.0, "net_worth": 10000.0},
            "family": _family_with_children_only(),
        }
    )
    service.save_service.save_life_state(state)
    inheritance = settle_estate(
        state.life_id,
        state.person_id,
        AssetState.from_life_state_dict(state.assets),
        FamilyState.from_life_state_dict(state.family),
        rules["inheritance"],
        "natural_death",
    )
    service.save_service.save_inheritance(state.life_id, inheritance.model_dump())

    continuation = service.continue_as_heir(state.life_id, "child-1")

    assert continuation["source_life_id"] == state.life_id
    assert continuation["heir_person_id"] == "child-1"
    assert continuation["new_life_id"]
    assert continuation["inheritance_amount"] == pytest.approx(4000.0)
    assert continuation["state"].person_id == "child-1"
    assert continuation["state"].flags["source_life_id"] == state.life_id


def test_continue_as_heir_fails_before_death(life_state, rules) -> None:
    service = GameCommandService()
    service.save_service.save_life_state(life_state)

    with pytest.raises(HeirContinuationError):
        service.continue_as_heir(life_state.life_id, "child-1")


def test_death_service_remains_only_death_confirmer(life_state, rules) -> None:
    context = make_context(life_state, rules)
    context.event_bus.publish(SimulationEventType.INHERITANCE_REQUESTED, "death", {})
    context.result_collector.confirm_death("already dead", death_type="natural_death")

    InheritanceService().run(context)

    assert InheritanceService.can_confirm_death is False
    assert DeathService.can_confirm_death is True

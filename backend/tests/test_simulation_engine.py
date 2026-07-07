from app.application.game_command_service import GameCommandService
from app.engine.simulation_engine import SimulationEngine


def test_simulation_engine_can_advance_one_year() -> None:
    service = GameCommandService(engine=SimulationEngine(rng_seed=1))
    state, choices = service.create_life()

    result = service.advance_one_year(
        state.life_id,
        {"annual_focus": choices[0]["id"]},
    )
    next_state, next_choices = service.get_life_state(state.life_id)

    assert result.life_id == state.life_id
    assert result.age_before == 0
    assert result.age_after == 1
    assert next_state.age == 1
    assert next_state.is_dead is False
    assert next_choices

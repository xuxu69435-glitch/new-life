from typing import Protocol

from app.engine.simulation_context import SimulationContext


class SimulationModule(Protocol):
    name: str
    can_confirm_death: bool

    def run(self, context: SimulationContext) -> None:
        ...


class ModuleRunner:
    def run(self, modules: list[SimulationModule], context: SimulationContext) -> None:
        for module in modules:
            module.run(context)

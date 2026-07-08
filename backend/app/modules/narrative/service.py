from typing import Any

from app.engine.simulation_context import SimulationContext
from app.modules.narrative.composer import AnnualNarrativeComposer
from app.modules.narrative.input_builder import build_annual_narrative_input
from app.modules.narrative.models import AnnualNarrativeResult


class NarrativeService:
    name = "narrative"
    can_confirm_death = False

    def __init__(self, composer: AnnualNarrativeComposer | None = None) -> None:
        self.composer = composer or AnnualNarrativeComposer()

    def run(self, context: SimulationContext) -> None:
        narrative_rules = context.rules.get("narrative", {})
        if not narrative_rules.get("use_narrative_v1", True):
            return

        input_data = build_annual_narrative_input(context)
        result = self.composer.compose(input_data)
        context.result_collector.set_narrative_result(result)

    def compose_from_payload(self, payload: dict[str, Any]) -> AnnualNarrativeResult:
        from app.modules.narrative.models import AnnualNarrativeInput

        return self.composer.compose(AnnualNarrativeInput.model_validate(payload))

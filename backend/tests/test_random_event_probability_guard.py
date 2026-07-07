import pytest

from app.infrastructure.errors import RuleValidationError
from app.rules.rule_validator import RuleValidator


def _direct_death_effect(event_id: str, name: str) -> dict:
    return {
        "type": "direct_death_candidate",
        "target": "death",
        "value": 1,
        "reason": name,
        "source_event_id": event_id,
        "source_event_name": name,
    }


def test_direct_death_probability_over_three_percent_fails(rules) -> None:
    rules["random_events"]["event_pool"] = [
        {
            "id": "a",
            "name": "Death A",
            "category": "direct_death",
            "stage": "any",
            "probability": 0.02,
            "direct_death": True,
            "weight": 1.0,
            "conditions": {},
            "effects": [_direct_death_effect("a", "Death A")],
        },
        {
            "id": "b",
            "name": "Death B",
            "category": "direct_death",
            "stage": "any",
            "probability": 0.02,
            "direct_death": True,
            "weight": 1.0,
            "conditions": {},
            "effects": [_direct_death_effect("b", "Death B")],
        },
    ]

    with pytest.raises(RuleValidationError):
        RuleValidator().validate(rules)

import pytest

from app.infrastructure.errors import RuleValidationError
from app.rules.rule_validator import RuleValidator


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
        },
        {
            "id": "b",
            "name": "Death B",
            "category": "direct_death",
            "stage": "any",
            "probability": 0.02,
            "direct_death": True,
            "weight": 1.0,
        },
    ]

    with pytest.raises(RuleValidationError):
        RuleValidator().validate(rules)

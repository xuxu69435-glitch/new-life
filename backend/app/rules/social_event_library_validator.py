import re

from app.infrastructure.errors import RuleValidationError
from app.modules.random_events.library_models import SocialEventLibraryV1
from app.modules.social.constants import RELATIONSHIP_TYPES
from app.rules.random_event_library_validator import ALLOWED_CONDITION_KEYS, ALLOWED_EFFECT_TYPES

WEIGHT_TIER_TO_WEIGHT = {
    "低概率": 1,
    "中低概率": 3,
    "中概率": 5,
    "中高概率": 8,
    "高概率": 12,
}

ALLOWED_SUB_CATEGORIES = {
    "school_social",
    "university_social",
    "workplace_social",
    "family_social",
    "neighborhood_or_adult_social",
}

SOCIAL_EVENT_ID_PATTERN = re.compile(r"^S\d{3}$")


class SocialEventLibraryValidator:
    def validate(self, library: SocialEventLibraryV1) -> None:
        if library.event_count != 60:
            raise RuleValidationError(
                f"Social library event_count must be 60, got {library.event_count}."
            )
        if len(library.events) != 60:
            raise RuleValidationError(
                f"Social library must contain 60 events, got {len(library.events)}."
            )

        seen_ids: set[str] = set()
        for index in range(1, 61):
            expected_id = f"S{index:03d}"
            if expected_id not in {event.event_id for event in library.events}:
                raise RuleValidationError(f"Missing required social event id: {expected_id}.")

        for event in library.events:
            if event.event_id in seen_ids:
                raise RuleValidationError(f"Duplicate social event id: {event.event_id}.")
            seen_ids.add(event.event_id)
            self._validate_event(event)

    def _validate_event(self, event) -> None:
        if not SOCIAL_EVENT_ID_PATTERN.match(event.event_id):
            raise RuleValidationError(f"Invalid social event id format: {event.event_id}.")
        if not event.title.strip():
            raise RuleValidationError(f"Event '{event.event_id}' must include title.")
        if event.category != "social":
            raise RuleValidationError(
                f"Event '{event.event_id}' category must be 'social', got '{event.category}'."
            )
        if event.sub_category not in ALLOWED_SUB_CATEGORIES:
            raise RuleValidationError(
                f"Event '{event.event_id}' has invalid sub_category: {event.sub_category}."
            )
        if event.age_range.min != event.conditions.get("min_age", event.age_range.min):
            pass
        if not event.event_text.strip():
            raise RuleValidationError(f"Event '{event.event_id}' must include event_text.")
        if not event.conditions:
            raise RuleValidationError(f"Event '{event.event_id}' must include trigger_conditions.")
        if event.weight <= 0 and event.repeat_policy != "once":
            raise RuleValidationError(f"Event '{event.event_id}' must have positive weight.")
        if event.cooldown_years is None:
            raise RuleValidationError(f"Event '{event.event_id}' must define cooldown_years.")
        if event.pool_type != "social":
            raise RuleValidationError(
                f"Event '{event.event_id}' must use pool_type=social."
            )
        if not event.choices:
            raise RuleValidationError(f"Event '{event.event_id}' must include choices.")

        if event.weight_tier in WEIGHT_TIER_TO_WEIGHT:
            expected_weight = WEIGHT_TIER_TO_WEIGHT[event.weight_tier]
            if event.weight != expected_weight:
                raise RuleValidationError(
                    f"Event '{event.event_id}' weight mismatch for tier "
                    f"'{event.weight_tier}': expected {expected_weight}, got {event.weight}."
                )

        for rel_type in event.target_relationship_types:
            if rel_type not in RELATIONSHIP_TYPES:
                raise RuleValidationError(
                    f"Event '{event.event_id}' has unsupported relationship type: {rel_type}."
                )

        for key in event.conditions:
            if key not in ALLOWED_CONDITION_KEYS and key not in {
                "sub_category",
                "is_enrolled",
                "years_worked_min",
                "years_worked_max",
                "school_year_min",
                "school_year_max",
                "education_graduated_this_year",
                "parents_alive",
                "has_sibling",
                "net_worth_above",
                "net_worth_below",
                "social_familiarity_min",
                "social_conflict_max",
            }:
                raise RuleValidationError(
                    f"Unknown condition field '{key}' in event '{event.event_id}'."
                )

        for choice in event.choices:
            if not choice.choice_id.strip():
                raise RuleValidationError(f"Choice in '{event.event_id}' must include choice_id.")
            if not choice.choice_text.strip():
                raise RuleValidationError(
                    f"Choice '{choice.choice_id}' must include text/choice_text."
                )
            if not choice.effects:
                raise RuleValidationError(f"Choice '{choice.choice_id}' must include effects.")
            for effect in choice.effects:
                effect_type = str(effect.get("type", "")).strip()
                if effect_type not in ALLOWED_EFFECT_TYPES:
                    raise RuleValidationError(
                        f"Unknown effect type '{effect_type}' in choice '{choice.choice_id}'."
                    )

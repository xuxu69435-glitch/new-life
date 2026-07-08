from app.infrastructure.errors import RuleValidationError
from app.rules.models import RandomEventRule


class RuleValidator:
    ALLOWED_EVENT_CATEGORIES = {
        "normal",
        "growth",
        "family",
        "health",
        "wealth",
        "direct_death",
    }
    ALLOWED_EFFECT_TYPES = {
        "attribute_change",
        "health_change",
        "asset_change",
        "direct_death_candidate",
        "narrative_tag",
        "flag_set",
    }

    def validate(self, rules: dict) -> None:
        self._validate_version(rules)
        self._validate_life_stages(rules)
        self._validate_default_attributes(rules)
        self._validate_health_rules(rules)
        self._validate_random_events(rules)
        self._validate_inheritance(rules)

    def _validate_version(self, rules: dict) -> None:
        version = rules.get("version")
        if not version or not str(version).strip():
            raise RuleValidationError("Rule config must include a non-empty version.")

    def _validate_life_stages(self, rules: dict) -> None:
        life_stages = rules.get("life_stages")
        if not life_stages:
            raise RuleValidationError("Rule config must include life stage rules.")

    def _validate_default_attributes(self, rules: dict) -> None:
        default_attributes = rules.get("default_attributes")
        if not default_attributes:
            raise RuleValidationError("Rule config must include default attribute rules.")

    def _validate_health_rules(self, rules: dict) -> None:
        health_rules = rules.get("health_lifetime")
        if not health_rules:
            raise RuleValidationError("Rule config must include health rules.")

        if not health_rules.get("health_score"):
            raise RuleValidationError("Health rules must include health_score config.")

        health_levels = health_rules.get("health_levels")
        if not health_levels:
            raise RuleValidationError("Health rules must include health_levels.")

        if not health_rules.get("natural_death"):
            raise RuleValidationError("Health rules must include natural_death config.")

        if not health_rules.get("warnings"):
            raise RuleValidationError("Health rules must include warnings config.")

        if not health_rules.get("disease_pool"):
            raise RuleValidationError("Health rules must include disease_pool.")

    def _validate_inheritance(self, rules: dict) -> None:
        inheritance = rules.get("inheritance")
        if not inheritance:
            raise RuleValidationError("Rule config must include inheritance rules.")

        if "tax_rate" not in inheritance:
            raise RuleValidationError("Inheritance rules must include tax_rate.")

        tax_rate = float(inheritance["tax_rate"])
        if tax_rate < 0 or tax_rate > 1:
            raise RuleValidationError("Inheritance tax_rate must be between 0 and 1.")
        if tax_rate != 0.2:
            raise RuleValidationError(
                f"Inheritance tax_rate must be 0.2 for the current scaffold, got {tax_rate}."
            )

        if "partner_share_ratio" not in inheritance:
            raise RuleValidationError("Inheritance rules must include partner_share_ratio.")
        if "descendant_share_ratio" not in inheritance:
            raise RuleValidationError("Inheritance rules must include descendant_share_ratio.")

        partner_ratio = float(inheritance["partner_share_ratio"])
        descendant_ratio = float(inheritance["descendant_share_ratio"])
        if abs(partner_ratio + descendant_ratio - 1.0) > 0.0001:
            raise RuleValidationError(
                "Inheritance partner_share_ratio and descendant_share_ratio must sum to 1."
            )

        if "continue_as_heir_enabled" not in inheritance:
            raise RuleValidationError(
                "Inheritance rules must include continue_as_heir_enabled."
            )

    def _validate_random_events(self, rules: dict) -> None:
        random_rules = rules.get("random_events")
        if not random_rules:
            raise RuleValidationError("Rule config must include random event rules.")

        if "direct_death_probability_limit" not in random_rules:
            raise RuleValidationError(
                "Random event rules must include direct_death_probability_limit."
            )

        event_pool = random_rules.get("event_pool")
        if not event_pool:
            raise RuleValidationError("Random event rules must include an event pool.")

        seen_ids: set[str] = set()
        for raw_event in event_pool:
            event = self._normalize_event(raw_event)
            if event.id in seen_ids:
                raise RuleValidationError(
                    f"Duplicate random event id detected: {event.id}."
                )
            seen_ids.add(event.id)

            if event.probability < 0:
                raise RuleValidationError(
                    f"Random event '{event.id}' probability cannot be less than 0."
                )
            if event.probability > 1:
                raise RuleValidationError(
                    f"Random event '{event.id}' probability cannot be greater than 1."
                )

            if event.category not in self.ALLOWED_EVENT_CATEGORIES:
                raise RuleValidationError(
                    f"Random event '{event.id}' has unsupported category: {event.category}."
                )

            self._validate_event_effects(raw_event, event)

        self._validate_direct_death_probability(random_rules, event_pool)

    def _validate_event_effects(self, raw_event: dict, event: RandomEventRule) -> None:
        effects = raw_event.get("effects", [])
        if effects is None:
            effects = []
        if isinstance(effects, dict):
            if effects:
                raise RuleValidationError(
                    f"Random event '{event.id}' effects must be a list."
                )
            effects = []
        if not isinstance(effects, list):
            raise RuleValidationError(f"Random event '{event.id}' effects must be a list.")

        has_direct_death_effect = False
        for effect in effects:
            if not isinstance(effect, dict):
                raise RuleValidationError(
                    f"Random event '{event.id}' contains a non-object effect."
                )
            effect_type = str(effect.get("type", "")).strip()
            if not effect_type:
                raise RuleValidationError(
                    f"Random event '{event.id}' has an effect with empty type."
                )
            if effect_type not in self.ALLOWED_EFFECT_TYPES:
                raise RuleValidationError(
                    f"Random event '{event.id}' has unsupported effect type: {effect_type}."
                )
            if effect_type == "direct_death_candidate":
                has_direct_death_effect = True
                if not event.direct_death:
                    raise RuleValidationError(
                        f"Random event '{event.id}' cannot include direct_death_candidate "
                        "when direct_death is false."
                    )
            elif event.direct_death:
                raise RuleValidationError(
                    f"Direct death event '{event.id}' can only include direct_death_candidate effects."
                )

            if effect_type == "attribute_change":
                if not effect.get("target"):
                    raise RuleValidationError(
                        f"Random event '{event.id}' attribute_change requires target."
                    )
                if "value" not in effect:
                    raise RuleValidationError(
                        f"Random event '{event.id}' attribute_change requires value."
                    )
            if effect_type == "health_change" and "value" not in effect:
                raise RuleValidationError(
                    f"Random event '{event.id}' health_change requires value."
                )
            if effect_type == "asset_change":
                if not effect.get("target"):
                    raise RuleValidationError(
                        f"Random event '{event.id}' asset_change requires target."
                    )
                if "value" not in effect:
                    raise RuleValidationError(
                        f"Random event '{event.id}' asset_change requires value."
                    )

        if event.direct_death and not has_direct_death_effect:
            raise RuleValidationError(
                f"Direct death event '{event.id}' must include direct_death_candidate effect."
            )

    def _validate_direct_death_probability(
        self,
        random_rules: dict,
        event_pool: list[dict],
    ) -> None:
        limit = float(random_rules["direct_death_probability_limit"])
        total = sum(
            float(event.get("probability", 0.0))
            for event in event_pool
            if event.get("direct_death") is True
        )
        if total > limit:
            raise RuleValidationError(
                f"Direct death event probability {total:.4f} exceeds limit {limit:.4f}."
            )

    def _normalize_event(self, raw_event: dict) -> RandomEventRule:
        payload = dict(raw_event)
        if "name" not in payload and "label" in payload:
            payload["name"] = payload["label"]
        if "category" not in payload:
            payload["category"] = "direct_death" if payload.get("direct_death") else "normal"
        return RandomEventRule.model_validate(payload)

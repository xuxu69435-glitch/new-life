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
        self._validate_education_rules(rules)
        self._validate_career_rules(rules)
        self._validate_family_rules(rules)
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

    def _validate_education_rules(self, rules: dict) -> None:
        education = rules.get("education")
        if not education:
            raise RuleValidationError("Rule config must include education rules.")

        stages = education.get("stages")
        if not stages:
            raise RuleValidationError("Education rules must include stages.")

        for stage in stages:
            if "min_age" not in stage or "max_age" not in stage:
                raise RuleValidationError(
                    f"Education stage '{stage.get('id', 'unknown')}' must include age range."
                )
            if int(stage["min_age"]) > int(stage["max_age"]):
                raise RuleValidationError(
                    f"Education stage '{stage.get('id', 'unknown')}' has invalid age range."
                )

    def _validate_career_rules(self, rules: dict) -> None:
        career = rules.get("career")
        if not career:
            raise RuleValidationError("Rule config must include career rules.")

        if "retirement_age" not in career:
            raise RuleValidationError("Career rules must include retirement_age.")

        paths = career.get("paths")
        if not paths:
            raise RuleValidationError("Career rules must include paths.")

        if "education_to_career_mapping" not in career:
            raise RuleValidationError("Career rules must include education_to_career_mapping.")

        seen_ids: set[str] = set()
        for path in paths:
            path_id = str(path.get("id", ""))
            if not path_id:
                raise RuleValidationError("Career path must include id.")
            if path_id in seen_ids:
                raise RuleValidationError(f"Duplicate career path id detected: {path_id}.")
            seen_ids.add(path_id)
            if "base_annual_income" not in path:
                raise RuleValidationError(f"Career path '{path_id}' must include base_annual_income.")
            if float(path["base_annual_income"]) < 0:
                raise RuleValidationError(
                    f"Career path '{path_id}' base_annual_income cannot be less than 0."
                )

    def _validate_family_rules(self, rules: dict) -> None:
        family = rules.get("family")
        if not family:
            raise RuleValidationError("Rule config must include family rules.")

        defaults = family.get("defaults")
        if not defaults:
            raise RuleValidationError("Family rules must include defaults.")

        for key in (
            "parent_child_relation",
            "father_relation",
            "mother_relation",
            "partner_relation",
            "family_pressure",
        ):
            if key not in defaults:
                raise RuleValidationError(f"Family defaults must include {key}.")
            value = int(defaults[key])
            if value < 0 or value > 100:
                raise RuleValidationError(f"Family default {key} must be between 0 and 100.")

        for section, min_key, max_key in (
            ("dating", "min_age", "max_age"),
            ("marriage", "min_age", "max_age"),
            ("childbirth", "min_age", "max_age"),
        ):
            block = family.get(section)
            if not block:
                raise RuleValidationError(f"Family rules must include {section}.")
            if int(block[min_key]) > int(block[max_key]):
                raise RuleValidationError(
                    f"Family {section} min_age cannot exceed max_age."
                )

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

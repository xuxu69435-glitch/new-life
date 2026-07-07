import json
from copy import deepcopy
from pathlib import Path

from app.infrastructure.errors import RuleLoadError, RuleValidationError
from app.rules.models import RuleSetSummary
from app.rules.rule_validator import RuleValidator
from app.rules.rule_version_manager import RuleVersionManager


class RuleLoader:
    def __init__(
        self,
        validator: RuleValidator | None = None,
        version_manager: RuleVersionManager | None = None,
    ) -> None:
        self.validator = validator or RuleValidator()
        self.version_manager = version_manager or RuleVersionManager()
        self._cache: dict[str, dict] = {}

    def load(self, rule_version: str) -> dict:
        self.version_manager.ensure_supported(rule_version)

        if rule_version in self._cache:
            return deepcopy(self._cache[rule_version])

        rule_path = self.version_manager.rule_file_path(rule_version)
        if not rule_path.exists():
            raise RuleLoadError(f"Rule file not found for version: {rule_version}.")

        try:
            raw_content = rule_path.read_text(encoding="utf-8")
            rules = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise RuleLoadError(
                f"Rule file format error for version {rule_version}: {exc.msg}."
            ) from exc
        except OSError as exc:
            raise RuleLoadError(
                f"Failed to read rule file for version {rule_version}: {exc}."
            ) from exc

        if not isinstance(rules, dict):
            raise RuleLoadError(
                f"Rule file for version {rule_version} must contain a JSON object."
            )

        loaded_version = str(rules.get("version", "")).strip()
        if loaded_version != rule_version:
            raise RuleValidationError(
                f"Rule file version mismatch: expected {rule_version}, got {loaded_version or 'empty'}."
            )

        self.validator.validate(rules)
        self._cache[rule_version] = deepcopy(rules)
        return deepcopy(rules)

    def load_default(self) -> dict:
        return self.load(self.version_manager.get_default_version())

    def clear_cache(self) -> None:
        self._cache.clear()

    def summarize(self, rule_version: str) -> RuleSetSummary:
        rules = self.load(rule_version)
        random_rules = rules.get("random_events", {})
        event_pool = random_rules.get("event_pool", [])
        direct_death_events = [
            event for event in event_pool if event.get("direct_death") is True
        ]
        return RuleSetSummary(
            version=rules["version"],
            life_stage_count=len(rules.get("life_stages", [])),
            random_event_count=len(event_pool),
            direct_death_event_count=len(direct_death_events),
            direct_death_probability_total=sum(
                float(event.get("probability", 0.0)) for event in direct_death_events
            ),
            direct_death_probability_limit=float(
                random_rules.get("direct_death_probability_limit", 0.03)
            ),
            inheritance_tax_rate=float(rules.get("inheritance", {}).get("tax_rate", 0.0)),
        )

    def validate_version(self, rule_version: str) -> None:
        self.load(rule_version)

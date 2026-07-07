from pathlib import Path

from app.infrastructure.config import settings
from app.infrastructure.errors import RuleValidationError


class RuleVersionManager:
    RULE_FILE_PATTERN = "rule_set_*.json"

    def __init__(
        self,
        data_dir: Path | None = None,
        default_version: str | None = None,
    ) -> None:
        self.data_dir = data_dir or Path(__file__).resolve().parent / "data"
        self.default_version = default_version or settings.default_rule_version
        self._supported_versions = self._discover_versions()

    def _discover_versions(self) -> set[str]:
        if not self.data_dir.exists():
            return set()

        versions: set[str] = set()
        for rule_file in self.data_dir.glob(self.RULE_FILE_PATTERN):
            if rule_file.name.endswith(".schema.json"):
                continue
            version = rule_file.stem.removeprefix("rule_set_")
            if version:
                versions.add(version)
        return versions

    def get_default_version(self) -> str:
        return self.default_version

    def get_version_for_new_life(self) -> str:
        return self.default_version

    def exists(self, rule_version: str) -> bool:
        return rule_version in self._supported_versions

    def list_versions(self) -> list[str]:
        return sorted(self._supported_versions)

    def rule_file_path(self, rule_version: str) -> Path:
        return self.data_dir / f"rule_set_{rule_version}.json"

    def ensure_supported(self, rule_version: str) -> None:
        if not self.exists(rule_version):
            raise RuleValidationError(
                f"Unsupported rule version: {rule_version}. "
                f"Available versions: {', '.join(self.list_versions()) or 'none'}."
            )

    def refresh(self) -> None:
        self._supported_versions = self._discover_versions()

    def ensure_default_available(self) -> None:
        if not self.exists(self.default_version):
            raise RuleValidationError(
                f"Default rule version '{self.default_version}' is not available."
            )

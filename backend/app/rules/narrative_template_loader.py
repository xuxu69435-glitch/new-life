import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.infrastructure.errors import RuleLoadError


class NarrativeTemplateLoader:
    def __init__(self) -> None:
        self._cache: dict[str, Any] | None = None

    @property
    def templates_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / "narrative_templates_v1.json"

    def load(self) -> dict[str, Any]:
        if self._cache is not None:
            return deepcopy(self._cache)

        if not self.templates_path.exists():
            raise RuleLoadError(f"Narrative templates not found: {self.templates_path}")

        payload = json.loads(self.templates_path.read_text(encoding="utf-8"))
        self._cache = deepcopy(payload)
        return deepcopy(payload)

    def clear_cache(self) -> None:
        self._cache = None

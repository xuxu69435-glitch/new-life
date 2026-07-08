import json
from copy import deepcopy
from pathlib import Path

from app.infrastructure.errors import RuleLoadError
from app.modules.legal.library_models import LegalEventLibraryV1


class LegalEventLibraryLoader:
    def __init__(self) -> None:
        self._cache: LegalEventLibraryV1 | None = None

    @property
    def library_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / "legal_event_library_v1.json"

    def load(self) -> LegalEventLibraryV1:
        if self._cache is not None:
            return deepcopy(self._cache)

        if not self.library_path.exists():
            raise RuleLoadError(f"Legal event library not found: {self.library_path}")

        payload = json.loads(self.library_path.read_text(encoding="utf-8"))
        library = LegalEventLibraryV1.model_validate(payload)
        self._cache = deepcopy(library)
        return deepcopy(library)

    def clear_cache(self) -> None:
        self._cache = None

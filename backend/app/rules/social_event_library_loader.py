import json
from copy import deepcopy
from pathlib import Path

from app.infrastructure.errors import RuleLoadError
from app.modules.random_events.library_models import SocialEventLibraryV1
from app.rules.social_event_library_validator import SocialEventLibraryValidator


class SocialEventLibraryLoader:
    def __init__(self, validator: SocialEventLibraryValidator | None = None) -> None:
        self.validator = validator or SocialEventLibraryValidator()
        self._cache: SocialEventLibraryV1 | None = None

    @property
    def library_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / "social_event_library_v1.json"

    def load(self) -> SocialEventLibraryV1:
        if self._cache is not None:
            return deepcopy(self._cache)

        if not self.library_path.exists():
            raise RuleLoadError(f"Social event library not found: {self.library_path}")

        try:
            raw_content = self.library_path.read_text(encoding="utf-8")
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise RuleLoadError(f"Social event library format error: {exc.msg}.") from exc
        except OSError as exc:
            raise RuleLoadError(f"Failed to read social event library: {exc}.") from exc

        library = SocialEventLibraryV1.model_validate(payload)
        self.validator.validate(library)
        self._cache = deepcopy(library)
        return deepcopy(library)

    def clear_cache(self) -> None:
        self._cache = None

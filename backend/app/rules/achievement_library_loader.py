import json
from copy import deepcopy
from pathlib import Path

from app.infrastructure.errors import RuleLoadError
from app.modules.achievement.library_models import AchievementLibraryV1


class AchievementLibraryLoader:
    def __init__(self) -> None:
        self._cache: AchievementLibraryV1 | None = None

    @property
    def library_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / "achievement_library_v1.json"

    def load(self) -> AchievementLibraryV1:
        if self._cache is not None:
            return deepcopy(self._cache)

        if not self.library_path.exists():
            raise RuleLoadError(f"Achievement library not found: {self.library_path}")

        payload = json.loads(self.library_path.read_text(encoding="utf-8"))
        library = AchievementLibraryV1.model_validate(payload)
        self._cache = deepcopy(library)
        return deepcopy(library)

    def clear_cache(self) -> None:
        self._cache = None

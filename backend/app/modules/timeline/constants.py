from typing import Final

SAVE_VERSION: Final[str] = "v1"
SNAPSHOT_VERSION: Final[str] = "v1"

ENTRY_IMPORTANCE: Final[dict[str, int]] = {
    "death": 100,
    "inheritance": 90,
    "legal_event": 80,
    "family": 70,
    "social": 60,
    "romance": 58,
    "education": 65,
    "career": 65,
    "mainline_task": 55,
    "achievement": 50,
    "milestone": 50,
    "health": 45,
    "random_event": 40,
    "asset": 40,
    "narrative": 30,
    "normal_summary": 10,
    "system": 5,
}

ALLOWED_ENTRY_TYPES: Final[set[str]] = {
    "random_event",
    "legal_event",
    "mainline_task",
    "achievement",
    "milestone",
    "education",
    "career",
    "family",
    "social",
    "romance",
    "health",
    "asset",
    "death",
    "inheritance",
    "narrative",
    "normal_summary",
    "system",
}

ALLOWED_EVENT_CATEGORIES: Final[set[str]] = {
    "random_event",
    "legal_event",
    "mainline_task",
    "achievement",
    "milestone",
    "education",
    "career",
    "family",
    "social",
    "health",
    "asset",
    "death",
    "inheritance",
    "narrative",
    "relationship",
    "system",
}

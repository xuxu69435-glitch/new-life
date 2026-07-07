import random


class ServerRandom:
    """Server-side random context. Frontend code never owns simulation randomness."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def random(self) -> float:
        return self._random.random()

    def choice(self, values: list[object]) -> object:
        return self._random.choice(values)

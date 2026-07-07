class DomainError(Exception):
    """Base exception for expected domain failures."""


class LifeAlreadyEndedError(DomainError):
    """Raised when a command tries to advance a dead life."""


class InvalidPlayerChoiceError(DomainError):
    """Raised when a submitted choice is not available for the current state."""


class RuleLoadError(DomainError):
    """Raised when rule files cannot be found or parsed."""


class RuleValidationError(DomainError):
    """Raised when loaded rules violate engine safety constraints."""


class RandomEventEffectError(DomainError):
    """Raised when a random event effect cannot be parsed or applied."""

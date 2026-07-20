"""Domain-level errors for the Story Bible plugin."""

from __future__ import annotations


class StoryBibleError(Exception):
    """Base class for Story Bible domain errors."""


class DuplicateTypeKeyError(StoryBibleError):
    """Raised when a project already has an entity type with this key."""


class DuplicateFieldKeyError(StoryBibleError):
    """Raised when an entity type already has a field with this internal key."""


class FieldValidationError(StoryBibleError):
    """Raised when a field value fails its declarative validation rules."""

    def __init__(self, field_internal_key: str, reason: str) -> None:
        self.field_internal_key = field_internal_key
        self.reason = reason
        super().__init__(f"Field '{field_internal_key}': {reason}")


class EntityTypeNotFoundError(StoryBibleError):
    """Raised when an operation references an unknown entity type."""

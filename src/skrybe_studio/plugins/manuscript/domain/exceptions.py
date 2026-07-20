"""Manuscript domain errors."""

from __future__ import annotations


class ManuscriptError(RuntimeError):
    """Base class for manuscript domain errors."""


class InvalidHierarchyError(ManuscriptError):
    """Raised when a node's type cannot be a child of its (attempted) parent's type."""


class CyclicHierarchyError(ManuscriptError):
    """Raised when a move would make a node its own ancestor."""


class NodeNotFoundError(ManuscriptError):
    """Raised when an operation references a manuscript node that does not exist."""

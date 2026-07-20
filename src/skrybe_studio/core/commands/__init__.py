"""The command registry."""

from skrybe_studio.core.commands.fuzzy import FuzzyMatch, fuzzy_match
from skrybe_studio.core.commands.registry import CommandRegistry, DuplicateCommandError

__all__ = ["CommandRegistry", "DuplicateCommandError", "FuzzyMatch", "fuzzy_match"]

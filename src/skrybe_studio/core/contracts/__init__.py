"""Typed contracts shared by the core and every plugin."""

from skrybe_studio.core.contracts.command import Command
from skrybe_studio.core.contracts.entity import Entity
from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.contracts.relationship import Relationship

__all__ = ["Command", "Entity", "Event", "Relationship"]

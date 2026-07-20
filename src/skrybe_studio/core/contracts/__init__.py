"""Typed contracts shared by the core and every plugin."""

from skrybe_studio.core.contracts.asset_lookup import AssetLookup
from skrybe_studio.core.contracts.command import Command
from skrybe_studio.core.contracts.entity import Entity
from skrybe_studio.core.contracts.entity_type import EntityTypeDefinition
from skrybe_studio.core.contracts.event import Event
from skrybe_studio.core.contracts.navigation import NavigationTarget
from skrybe_studio.core.contracts.relationship import Relationship
from skrybe_studio.core.contracts.relationship_type import RelationshipTypeDefinition

__all__ = [
    "AssetLookup",
    "Command",
    "Entity",
    "EntityTypeDefinition",
    "Event",
    "NavigationTarget",
    "Relationship",
    "RelationshipTypeDefinition",
]

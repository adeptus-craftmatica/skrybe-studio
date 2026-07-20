"""Optional manuscript-to-asset relationships, resolved through the shared
`AssetLookup` capability - never by importing the Asset Library plugin.

If the Asset Library plugin is disabled or fails to load, `context.services.
get(AssetLookup)` simply returns `None`: relationships (which reference an
asset only by UUID) remain intact and loadable, and callers here degrade
to "unavailable" rather than raising.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from skrybe_studio.core.contracts.asset_lookup import AssetLookup
from skrybe_studio.core.entities.relationships import RelationshipService
from skrybe_studio.core.services.container import ServiceContainer
from skrybe_studio.plugins.manuscript.domain.models import PLUGIN_ID

COVER_ASSET_RELATIONSHIP = "manuscript.cover_asset"
REFERENCE_ASSET_RELATIONSHIP = "manuscript.reference_asset"
ICON_ASSET_RELATIONSHIP = "manuscript.icon_asset"


class ManuscriptAssetService:
    def __init__(self, relationships: RelationshipService, services: ServiceContainer) -> None:
        self._relationships = relationships
        self._services = services

    def _lookup(self) -> AssetLookup | None:
        return self._services.get(AssetLookup)

    @property
    def is_asset_library_available(self) -> bool:
        return self._lookup() is not None

    def set_cover_asset(self, node_id: UUID, asset_id: UUID) -> None:
        for existing in self._relationships.for_entity(node_id):
            if existing.relationship_type == COVER_ASSET_RELATIONSHIP:
                self._relationships.delete(existing.id)
        self._relationships.create(
            source_entity_id=node_id,
            target_entity_id=asset_id,
            relationship_type=COVER_ASSET_RELATIONSHIP,
            plugin_owner=PLUGIN_ID,
        )

    def clear_cover_asset(self, node_id: UUID) -> None:
        for existing in self._relationships.for_entity(node_id):
            if existing.relationship_type == COVER_ASSET_RELATIONSHIP:
                self._relationships.delete(existing.id)

    def get_cover_asset_id(self, node_id: UUID) -> UUID | None:
        for relationship in self._relationships.for_entity(node_id):
            if (
                relationship.relationship_type == COVER_ASSET_RELATIONSHIP
                and relationship.source_entity_id == node_id
            ):
                return relationship.target_entity_id
        return None

    def resolve_cover_thumbnail(self, node_id: UUID) -> Path | None:
        asset_id = self.get_cover_asset_id(node_id)
        lookup = self._lookup()
        if asset_id is None or lookup is None or not lookup.asset_exists(asset_id):
            return None
        return lookup.resolve_thumbnail(asset_id)

    def cover_asset_title(self, node_id: UUID) -> str | None:
        asset_id = self.get_cover_asset_id(node_id)
        lookup = self._lookup()
        if asset_id is None or lookup is None:
            return None
        return lookup.asset_title(asset_id)

    def list_available_assets(self) -> list[tuple[UUID, str]]:
        lookup = self._lookup()
        return lookup.list_assets() if lookup is not None else []

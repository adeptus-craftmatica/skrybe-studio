"""Pydantic schema for `manifest.json`, validated at discovery time."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_API_VERSIONS = frozenset({"1"})


class PluginManifest(BaseModel):
    """Validated shape of a plugin's `manifest.json`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    version: str
    api_version: str
    description: str = ""
    author: str = ""
    entrypoint: str
    capabilities: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    optional_requires: list[str] = Field(default_factory=list)

    @field_validator("id", "name", "version", "entrypoint")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("entrypoint")
    @classmethod
    def _entrypoint_format(cls, value: str) -> str:
        module_path, _, class_name = value.partition(":")
        if not module_path or not class_name:
            raise ValueError("entrypoint must be in 'module.path:ClassName' format")
        return value

    def is_api_version_supported(self) -> bool:
        return self.api_version in SUPPORTED_API_VERSIONS

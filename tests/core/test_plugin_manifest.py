from __future__ import annotations

import pytest
from pydantic import ValidationError

from skrybe_studio.core.plugins.manifest import PluginManifest

VALID = {
    "id": "com.example.demo",
    "name": "Demo",
    "version": "0.1.0",
    "api_version": "1",
    "entrypoint": "some.module:SomeClass",
}


def test_valid_manifest_parses() -> None:
    manifest = PluginManifest.model_validate(VALID)
    assert manifest.id == "com.example.demo"
    assert manifest.is_api_version_supported()


def test_unsupported_api_version_is_detected() -> None:
    manifest = PluginManifest.model_validate({**VALID, "api_version": "99"})
    assert not manifest.is_api_version_supported()


def test_blank_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PluginManifest.model_validate({**VALID, "id": "  "})


def test_entrypoint_without_class_separator_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PluginManifest.model_validate({**VALID, "entrypoint": "some.module.SomeClass"})


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PluginManifest.model_validate({**VALID, "unexpected_field": True})


def test_defaults_are_empty_lists() -> None:
    manifest = PluginManifest.model_validate(VALID)
    assert manifest.capabilities == []
    assert manifest.requires == []
    assert manifest.optional_requires == []

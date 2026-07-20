"""Design tokens: the single source of truth for spacing, type, radii, and color.

No widget or plugin should hardcode a color or spacing value - everything
should flow from a `DesignTokens` instance so retheming stays centralized.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpacingTokens:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24


@dataclass(frozen=True, slots=True)
class RadiusTokens:
    sm: int = 3
    md: int = 5


@dataclass(frozen=True, slots=True)
class TypographyTokens:
    # Empty means "don't override" - Qt already selects the correct native UI
    # font per platform. A CSS-style web font stack (e.g. "-apple-system, ...,
    # sans-serif") looks reasonable but Qt Style Sheets resolve font-family
    # differently than CSS: "-apple-system" isn't a real font name Qt can find,
    # and the generic "sans-serif" keyword forces a slow font-alias-population
    # pass on every launch with a "missing font family" warning. Only set this
    # to a real, installed font name (e.g. once a bundled font ships).
    font_family: str = ""
    size_small: int = 11
    size_body: int = 13
    size_heading: int = 15
    size_title: int = 18
    weight_regular: int = 400
    weight_medium: int = 500
    weight_bold: int = 600


@dataclass(frozen=True, slots=True)
class ColorTokens:
    background: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_text: str
    selection: str
    error: str
    warning: str
    success: str


@dataclass(frozen=True, slots=True)
class DesignTokens:
    colors: ColorTokens
    spacing: SpacingTokens
    radius: RadiusTokens
    typography: TypographyTokens


_LIGHT_COLORS = ColorTokens(
    background="#F5F5F4",
    surface="#FFFFFF",
    surface_alt="#EDECEA",
    border="#D8D6D2",
    text="#1E1E1C",
    text_muted="#6B6A66",
    accent="#3D5A80",
    accent_text="#FFFFFF",
    selection="#CBD8E8",
    error="#B3261E",
    warning="#8A5A00",
    success="#2E6B3E",
)

_DARK_COLORS = ColorTokens(
    background="#1E1F21",
    surface="#26272A",
    surface_alt="#2E3033",
    border="#3B3D41",
    text="#E7E6E3",
    text_muted="#9A9C9F",
    accent="#7DA0C4",
    accent_text="#12222F",
    selection="#324459",
    error="#E57A73",
    warning="#D8AE55",
    success="#7FBF8F",
)

LIGHT_TOKENS = DesignTokens(
    colors=_LIGHT_COLORS,
    spacing=SpacingTokens(),
    radius=RadiusTokens(),
    typography=TypographyTokens(),
)

DARK_TOKENS = DesignTokens(
    colors=_DARK_COLORS,
    spacing=SpacingTokens(),
    radius=RadiusTokens(),
    typography=TypographyTokens(),
)

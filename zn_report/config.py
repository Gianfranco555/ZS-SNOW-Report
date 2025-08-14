"""Configuration for the Zscaler ServiceNow Incident Reporter."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from zn_report.constants import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_PALETTE,
    DEFAULT_TITLE,
)


class ConfigurationError(ValueError):
    """Custom exception for configuration errors."""


@dataclass
class Branding:
    """Branding configuration."""

    logo_path: str | None = None
    footer: str | None = None


@dataclass
class Palette:
    """Color palette."""

    primary: str
    secondary: str
    accent: str
    muted: str
    categorical: list[str]

    def __post_init__(self):
        """Validate palette configuration."""
        if not (
            self.categorical
            and isinstance(self.categorical, list)
            and all(isinstance(s, str) for s in self.categorical)
        ):
            raise ValueError(
                "style.palette.categorical must be a non-empty list of strings"
            )


@dataclass
class Style:
    """Style configuration."""

    palette: Palette
    font_family: str


@dataclass
class Layout:
    """Layout configuration."""

    show_resolution_codes_chart: bool = True
    show_top_tags_chart: bool = True


@dataclass
class Config:
    """Top-level configuration."""

    title: str
    branding: Branding
    style: Style
    layout: Layout


DEFAULT_CONFIG = Config(
    title=DEFAULT_TITLE,
    branding=Branding(),
    style=Style(
        palette=Palette(**DEFAULT_PALETTE),
        font_family=DEFAULT_FONT_FAMILY,
    ),
    layout=Layout(),
)


def to_dict(cfg: Config) -> dict[str, Any]:
    """Converts a Config object to a dictionary."""
    return asdict(cfg)


def deep_merge(base: dict, override: dict) -> dict:
    """Merge two dictionaries recursively.

    Lists are replaced, scalars are overwritten, and dicts are merged.
    """
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def coerce_config(d: dict) -> Config:
    """Convert a merged dict into typed dataclasses.

    Raise ConfigurationError on missing/invalid fields.
    """
    # No deepcopy needed, as load_config provides a fresh dict.
    cfg = d

    # --- Main Coercion and Construction ---
    try:
        # Validate that nested sections are dictionaries
        for section in ["branding", "layout", "style"]:
            if not isinstance(cfg.get(section), dict):
                raise ConfigurationError(
                    f"Config section '{section}' must be a dictionary."
                )

        if not isinstance(cfg.get("style", {}).get("palette"), dict):
            raise ConfigurationError(
                "Config section 'style.palette' must be a dictionary."
            )

        # Let dataclass constructors handle the rest.
        # __post_init__ will run validation.
        return Config(
            title=cfg["title"],
            branding=Branding(**cfg["branding"]),
            style=Style(
                palette=Palette(**cfg["style"]["palette"]),
                font_family=cfg["style"]["font_family"],
            ),
            layout=Layout(**cfg["layout"]),
        )
    except (ValueError, TypeError, KeyError) as e:
        # Catch validation errors from __post_init__ or construction errors
        raise ConfigurationError(f"Invalid configuration: {e}") from e


def load_config(settings: dict | None = None) -> Config:
    """If None, return DEFAULT_CONFIG.

    Else, deep_merge(to_dict(DEFAULT_CONFIG), settings) → coerce_config.
    """
    if settings is None:
        return DEFAULT_CONFIG

    base_config = to_dict(DEFAULT_CONFIG)
    merged_config = deep_merge(base_config, settings)
    return coerce_config(merged_config)

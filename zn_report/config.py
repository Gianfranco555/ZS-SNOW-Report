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
class Summary:
    """Summary configuration."""

    class Provider(str, Enum):
        """Providers for summary generation."""

        NONE = "none"
        LOCAL = "local"
        OPENAI = "openai"

    enabled: bool = True
    provider: Provider = Provider.LOCAL
    max_chars: int = 700


@dataclass
class Config:
    """Top-level configuration."""

    title: str
    branding: Branding
    style: Style
    layout: Layout
    summary: Summary


DEFAULT_CONFIG = Config(
    title=DEFAULT_TITLE,
    branding=Branding(),
    style=Style(
        palette=Palette(**DEFAULT_PALETTE),
        font_family=DEFAULT_FONT_FAMILY,
    ),
    layout=Layout(),
    summary=Summary(),
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

    Raise ValueError on missing/invalid fields.
    """
    cfg = deepcopy(d)

    # --- Validation and Coercion ---
    try:
        summary_cfg = cfg["summary"]
        provider_str = summary_cfg["provider"]
        summary_cfg["provider"] = Summary.Provider(provider_str)

        if summary_cfg["max_chars"] <= 0:
            raise ValueError("summary.max_chars must be > 0")
    except ValueError as e:
        raise ValueError(f"Invalid summary configuration: {e}")
    except KeyError as e:
        raise ValueError(f"Missing key in summary configuration: {e}")

    try:
        palette_cfg = cfg["style"]["palette"]
        categorical = palette_cfg["categorical"]
        if not (
            categorical
            and isinstance(categorical, list)
            and all(isinstance(s, str) for s in categorical)
        ):
            raise ValueError(
                "style.palette.categorical must be a non-empty list of strings"
            )
    except KeyError as e:
        raise ValueError(f"Missing key in style configuration: {e}")

    # --- Dataclass Construction ---
    try:
        return Config(
            title=cfg["title"],
            branding=Branding(**cfg["branding"]),
            style=Style(
                palette=Palette(**cfg["style"]["palette"]),
                font_family=cfg["style"]["font_family"],
            ),
            layout=Layout(**cfg["layout"]),
            summary=Summary(**cfg["summary"]),
        )
    except (TypeError, KeyError) as e:
        raise ValueError(
            f"Configuration is missing required fields or has unexpected fields: {e}"
        )


def load_config(settings: dict | None = None) -> Config:
    """If None, return DEFAULT_CONFIG.

    Else, deep_merge(to_dict(DEFAULT_CONFIG), settings) → coerce_config.
    """
    if settings is None:
        return DEFAULT_CONFIG

    base_config = to_dict(DEFAULT_CONFIG)
    merged_config = deep_merge(base_config, settings)
    return coerce_config(merged_config)

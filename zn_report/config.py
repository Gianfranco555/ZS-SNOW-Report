"""Configuration for the Zscaler ServiceNow Incident Reporter."""

from __future__ import annotations

from dataclasses import dataclass, asdict
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

        LOCAL = "local"

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


def load_config(path: str) -> dict[str, Any]:
    """Load the configuration from a YAML file.

    Args:
        path: The path to the YAML configuration file.

    Returns:
        A dictionary containing the configuration.
    """
    # TODO: Implement YAML parsing.
    # For now, this is a stub that returns an empty dict.
    print(f"TODO: Load config from {path}")
    return {}

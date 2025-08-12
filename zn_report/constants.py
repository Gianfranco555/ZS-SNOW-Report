"""Constants for the Zscaler ServiceNow Incident Reporter."""

from __future__ import annotations

DEFAULT_SEED: int = 42

# Data loading
REQUIRED_HEADERS: frozenset[str] = frozenset(
    {
        "sys_tags",
        "comments",
        "work_notes",
        "assigned_to",
        "opened_at",
        "state",
        "resolved_at",
        "u_original_assignment_group",
        "close_code",
    }
)

# Branding & style defaults
DEFAULT_TITLE = "Zscaler Incident Report"
DEFAULT_FONT_FAMILY = "Inter, Arial, sans-serif"
DEFAULT_PALETTE = {
    "primary": "#2F6FE4",
    "secondary": "#6C757D",
    "accent": "#F4B400",
    "muted": "#D0D3D4",
    "categorical": [
        "#2F6FE4",
        "#00A1D6",
        "#7CB342",
        "#F4B400",
        "#E67E22",
        "#8E44AD",
        "#C0392B",
    ],
}


def apply_global_seed(seed: int = DEFAULT_SEED) -> None:
    """Seeds both random and (if available) numpy.random.

    Import numpy inside the function; if not installed, skip silently.
    """
    import random

    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass

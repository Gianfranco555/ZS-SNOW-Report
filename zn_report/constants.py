"""Constants for the Zscaler ServiceNow Incident Reporter."""

from __future__ import annotations

import random


def seed_rng(seed: int | float | str | bytes | bytearray | None = None) -> None:
    """Seed the random number generator.

    Args:
        seed: The seed to use for the RNG. If None, the RNG is not seeded.
    """
    if seed is not None:
        random.seed(seed)


# TODO: Add other constants as needed.

"""Save/load Q-network params with flax msgpack serialization."""

from __future__ import annotations

from pathlib import Path

import flax.serialization as fser


def save_params(path: str, params) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(fser.to_bytes(params))


def load_params(template, path: str):
    """Load into the pytree structure of `template` (e.g. a freshly init'd params)."""
    return fser.from_bytes(template, Path(path).read_bytes())

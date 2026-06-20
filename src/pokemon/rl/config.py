"""Hyperparameters for the option-scoring DQN."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DQNConfig:
    gamma: float = 0.99
    lr: float = 1e-3
    batch_size: int = 128
    replay_capacity: int = 100_000
    hidden: tuple[int, ...] = (256, 256)
    target_update_interval: int = 1000  # unused with Polyak (kept for reference)
    tau: float = 0.01  # Polyak soft target-update rate (per gradient step)
    eps_start: float = 1.0
    eps_end: float = 0.05
    eps_decay_steps: int = 40_000
    # Max options stored per decision (pad/truncate the next-state option set).
    k_max: int = 64
    seed: int = 0

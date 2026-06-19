"""Head-to-head evaluation: greedy win-rate vs an opponent."""

from __future__ import annotations

from collections.abc import Callable

from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon.rl import rollout


def evaluate(
    act: Callable[[dict], list[int]], opponent=random_agent, n_games: int = 50, seed: int = 0
) -> float:
    wins = 0
    for g in range(n_games):
        _, terminal_reward = rollout.play_game(act=act, opponent=opponent, seed=seed + g)
        wins += int(terminal_reward > 0)
    return wins / n_games

"""Drive one CABT game and turn our decisions into DQN transitions.

M0 policy is uniform-random; M1 swaps in epsilon-greedy over the Q-network.
"""

from __future__ import annotations

import copy
import random

import kaggle_environments as kaggle
import numpy as np
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon.decks import FIRE_DECK
from pokemon.rl import features
from pokemon.rl import reward as rwd


def make_collector(records: list, rng: random.Random):
    def agent(obs: dict) -> list[int]:
        if obs["select"] is None:
            return FIRE_DECK
        opts = obs["select"]["option"]
        choice = rng.sample(range(len(opts)), obs["select"]["maxCount"])
        records.append({"obs": copy.deepcopy(obs), "choice": choice})
        return choice

    return agent


def play_game(opponent=random_agent, gamma: float = 0.99, seed: int | None = None):
    rng = random.Random(seed)
    records: list = []
    env = kaggle.make("cabt", debug=True)
    env.reset()
    steps = env.run([make_collector(records, rng), opponent])
    terminal_reward = float(steps[-1][0].get("reward") or 0.0)

    transitions: list[dict] = []
    n = len(records)
    for i, rec in enumerate(records):
        obs = rec["obs"]
        state, options, _ = features.encode_decision(obs)
        chosen = rec["choice"][0]  # M0: pick-1 (top-k approximation deferred)
        last = i == n - 1
        if last:
            next_state = np.zeros_like(state)
            next_options = np.zeros((0, options.shape[1]), np.float32)
            reward = rwd.shaped_reward(obs, None, gamma, terminal_reward)
            done = True
        else:
            next_obs = records[i + 1]["obs"]
            next_state, next_options, _ = features.encode_decision(next_obs)
            reward = rwd.shaped_reward(obs, next_obs, gamma)
            done = False
        transitions.append(
            {
                "state": state,
                "option": options[chosen],
                "reward": reward,
                "next_state": next_state,
                "next_options": next_options,
                "done": done,
            }
        )
    return transitions, terminal_reward

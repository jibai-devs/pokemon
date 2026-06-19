"""Drive one CABT game and turn our decisions into DQN transitions.

The acting policy is injected as `act(obs) -> list[int]`; default is uniform
random (M0 behavior). M1 passes an epsilon-greedy policy over the Q-network.
"""

from __future__ import annotations

import copy
import random
from collections.abc import Callable

import kaggle_environments as kaggle
import numpy as np
from kaggle_environments.envs.cabt.cabt import random_agent

from pokemon.decks import FIRE_DECK
from pokemon.rl import features
from pokemon.rl import reward as rwd


def make_collector(records: list, act: Callable[[dict], list[int]]):
    def agent(obs: dict) -> list[int]:
        if obs["select"] is None:
            return FIRE_DECK
        choice = act(obs)
        records.append({"obs": copy.deepcopy(obs), "choice": choice})
        return choice

    return agent


def _random_act(rng: random.Random) -> Callable[[dict], list[int]]:
    def act(obs: dict) -> list[int]:
        opts = obs["select"]["option"]
        return rng.sample(range(len(opts)), obs["select"]["maxCount"])

    return act


def play_game(act=None, opponent=random_agent, gamma: float = 0.99, seed: int | None = None):
    if act is None:
        act = _random_act(random.Random(seed))
    records: list = []
    env = kaggle.make("cabt", debug=True)
    env.reset()
    steps = env.run([make_collector(records, act), opponent])
    terminal_reward = float(steps[-1][0].get("reward") or 0.0)

    transitions: list[dict] = []
    n = len(records)
    for i, rec in enumerate(records):
        obs = rec["obs"]
        state, options, _ = features.encode_decision(obs)
        chosen = rec["choice"][0]  # store the primary (highest-Q / first) option
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

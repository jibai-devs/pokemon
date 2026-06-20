"""Drive one CABT game and turn our decisions into DQN transitions.

The acting policy is injected as `act(obs) -> list[int]`; default is uniform
random (M0 behavior). M1 passes an epsilon-greedy policy over the Q-network.
"""

from __future__ import annotations

import copy
import logging
import random
import time
from collections.abc import Callable

import numpy as np

# kaggle_environments emits a ~30-line open_spiel INFO banner at import (via its
# own logger + stdout handler that it configures itself). Suppress just that
# import-time noise — it would otherwise repeat in every spawn rollout worker —
# then restore the prior logging state. This is the first kaggle import in the
# train/eval/worker path, so it covers them all.
_prev_disable = logging.root.manager.disable
logging.disable(logging.INFO)
import kaggle_environments as kaggle  # noqa: E402
from kaggle_environments.envs.cabt.cabt import random_agent  # noqa: E402

logging.disable(_prev_disable)

from pokemon.decks import FIRE_DECK  # noqa: E402
from pokemon.rl import features  # noqa: E402
from pokemon.rl import reward as rwd  # noqa: E402


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


def _timed(fn: Callable, timers: dict, key: str) -> Callable:
    """Wrap an agent callback to accumulate wall time it spends into timers[key]."""

    def wrapped(obs: dict):
        t = time.perf_counter()
        try:
            return fn(obs)
        finally:
            timers[key] = timers.get(key, 0.0) + (time.perf_counter() - t)

    return wrapped


def play_game(
    act=None,
    opponent=random_agent,
    gamma: float = 0.99,
    seed: int | None = None,
    timers: dict | None = None,
):
    """Play one game and return (transitions, terminal_reward).

    If `timers` (a dict) is passed, accumulate a wall-time breakdown into it —
    `setup` (make+reset), `agent` (our callback: encode + scorer + record),
    `opponent`, `run` (total env.run, which contains agent+opponent), and `post`
    (our transition-assembly encoding). Engine/libcg time ~= run minus agent and
    opponent.
    Zero overhead when `timers is None` (no wrapping, no clock reads)."""
    if act is None:
        act = _random_act(random.Random(seed))
    records: list = []

    if timers is None:
        env = kaggle.make("cabt", debug=True)
        env.reset()
        steps = env.run([make_collector(records, act), opponent])
    else:
        t = time.perf_counter()
        env = kaggle.make("cabt", debug=True)
        env.reset()
        timers["setup"] = timers.get("setup", 0.0) + (time.perf_counter() - t)
        agent = _timed(make_collector(records, act), timers, "agent")
        opp = _timed(opponent, timers, "opponent")
        t = time.perf_counter()
        steps = env.run([agent, opp])
        timers["run"] = timers.get("run", 0.0) + (time.perf_counter() - t)
    terminal_reward = float(steps[-1][0].get("reward") or 0.0)

    t_post = time.perf_counter() if timers is not None else 0.0
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
    if timers is not None:
        timers["post"] = timers.get("post", 0.0) + (time.perf_counter() - t_post)
    return transitions, terminal_reward

"""Action selection over the engine's offered option list (ε-greedy / greedy)."""

from __future__ import annotations

import jax.numpy as jnp
import numpy as np

from pokemon.rl import features, net


def select_action(
    model: net.QNet, params, obs: dict, eps: float, rng: np.random.Generator
) -> list[int]:
    opts = obs["select"]["option"]
    n = len(opts)
    max_count = obs["select"]["maxCount"]
    if rng.random() < eps:
        idx = rng.choice(n, size=max_count, replace=False)
        return [int(i) for i in idx]
    state, options, _ = features.encode_decision(obs)
    q = np.asarray(net.q_values(model, params, jnp.asarray(state), jnp.asarray(options)))
    order = np.argsort(-q)[:max_count]
    return [int(i) for i in order]


def greedy_act(model: net.QNet, params):
    rng = np.random.default_rng(0)

    def act(obs: dict) -> list[int]:
        return select_action(model, params, obs, 0.0, rng)

    return act


def eps_act(model: net.QNet, params, eps: float, rng: np.random.Generator):
    def act(obs: dict) -> list[int]:
        return select_action(model, params, obs, eps, rng)

    return act

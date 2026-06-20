"""Action selection over the engine's offered option list (ε-greedy / greedy)."""

from __future__ import annotations

import jax.numpy as jnp
import numpy as np

from pokemon.rl import features, net

K_MAX = 64  # default padded option width for the jitted scorer (matches DQNConfig.k_max)


def select_action(
    model: net.QNet,
    params,
    obs: dict,
    eps: float,
    rng: np.random.Generator,
    k_max: int = K_MAX,
) -> list[int]:
    opts = obs["select"]["option"]
    n = len(opts)
    max_count = obs["select"]["maxCount"]
    if rng.random() < eps:
        idx = rng.choice(n, size=max_count, replace=False)
        return [int(i) for i in idx]
    state, options, mask, _ = features.encode_decision_padded(obs, k_max)
    q = np.asarray(
        net.q_values_masked(
            model.apply, params, jnp.asarray(state), jnp.asarray(options), jnp.asarray(mask)
        )
    )
    order = np.argsort(-q)[:max_count]
    return [int(i) for i in order]


def greedy_act(model: net.QNet, params, k_max: int = K_MAX):
    rng = np.random.default_rng(0)

    def act(obs: dict) -> list[int]:
        return select_action(model, params, obs, 0.0, rng, k_max)

    return act


def eps_act(model: net.QNet, params, eps: float, rng: np.random.Generator, k_max: int = K_MAX):
    def act(obs: dict) -> list[int]:
        return select_action(model, params, obs, eps, rng, k_max)

    return act

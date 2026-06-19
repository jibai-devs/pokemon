"""Option-scoring Q-network: Q(state, option) -> scalar."""

from __future__ import annotations

import flax.linen as nn
import jax.numpy as jnp


class QNet(nn.Module):
    hidden: tuple[int, ...] = (256, 256)

    @nn.compact
    def __call__(self, state: jnp.ndarray, option: jnp.ndarray) -> jnp.ndarray:
        # state/option broadcast-concatenate on the last axis.
        x = jnp.concatenate([state, option], axis=-1)
        for h in self.hidden:
            x = nn.relu(nn.Dense(h)(x))
        return jnp.squeeze(nn.Dense(1)(x), axis=-1)


def init_params(model: QNet, rng, state_dim: int, option_dim: int):
    return model.init(rng, jnp.zeros((state_dim,)), jnp.zeros((option_dim,)))


def q_values(model: QNet, params, state: jnp.ndarray, options: jnp.ndarray) -> jnp.ndarray:
    """Score every option in a single decision. state[S], options[K,O] -> [K]."""
    tiled = jnp.broadcast_to(state[None, :], (options.shape[0], state.shape[0]))
    # flax's `apply` is typed to optionally return mutated vars; wrap so the
    # static type is a plain array (no mutable collections are requested here).
    return jnp.asarray(model.apply(params, tiled, options))


def q_values_batched(model: QNet, params, states: jnp.ndarray, options: jnp.ndarray) -> jnp.ndarray:
    """Score a batch of option sets. states[B,S], options[B,K,O] -> [B,K]."""
    b, k, _ = options.shape
    tiled = jnp.broadcast_to(states[:, None, :], (b, k, states.shape[-1]))
    return jnp.asarray(model.apply(params, tiled, options))

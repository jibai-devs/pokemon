"""Double-DQN training step over the option-scoring Q-network."""

from __future__ import annotations

import jax
import jax.numpy as jnp
import optax
from flax.training.train_state import TrainState

from pokemon.rl import net


def create_train_state(model: net.QNet, params, lr: float) -> TrainState:
    return TrainState.create(apply_fn=model.apply, params=params, tx=optax.adam(lr))


def make_update_step(model: net.QNet, gamma: float):
    @jax.jit
    def update_step(state: TrainState, target_params, batch):
        def loss_fn(params):
            q_sa = jnp.asarray(model.apply(params, batch["state"], batch["option"]))  # [B]
            q_next_online = net.q_values_batched(
                model, params, batch["next_state"], batch["next_options"]
            )  # [B,K]
            q_next_target = net.q_values_batched(
                model, target_params, batch["next_state"], batch["next_options"]
            )  # [B,K]
            mask = batch["next_mask"]
            masked = jnp.where(mask, q_next_online, -jnp.inf)
            next_act = jnp.argmax(masked, axis=-1)  # [B]
            q_next = jnp.take_along_axis(q_next_target, next_act[:, None], axis=1)[:, 0]  # [B]
            has_next = jnp.any(mask, axis=-1)
            q_next = jnp.where(has_next, q_next, 0.0)
            target = jax.lax.stop_gradient(
                batch["reward"] + gamma * (1.0 - batch["done"]) * q_next
            )
            return optax.huber_loss(q_sa, target).mean()

        loss, grads = jax.value_and_grad(loss_fn)(state.params)
        state = state.apply_gradients(grads=grads)
        return state, loss

    return update_step

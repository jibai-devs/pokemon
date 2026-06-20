import jax.numpy as jnp

from pokemon.rl import learner


def test_soft_update_moves_target_toward_online():
    target = {"w": jnp.zeros(3)}
    online = {"w": jnp.ones(3)}
    new = learner.soft_update(target, online, tau=0.1)
    # (1 - tau) * 0 + tau * 1 == 0.1
    assert abs(float(new["w"][0]) - 0.1) < 1e-6


def test_soft_update_tau_one_copies_online():
    target = {"w": jnp.zeros(2)}
    online = {"w": jnp.full(2, 5.0)}
    new = learner.soft_update(target, online, tau=1.0)
    assert float(new["w"][0]) == 5.0

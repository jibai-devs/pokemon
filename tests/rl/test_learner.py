import jax
import jax.numpy as jnp
import numpy as np

from pokemon.rl import features, learner, net


def _toy_batch(b=16):
    rng = np.random.default_rng(0)
    arrs = {
        "state": rng.standard_normal((b, features.STATE_DIM)).astype(np.float32),
        "option": rng.standard_normal((b, features.OPTION_DIM)).astype(np.float32),
        "reward": np.ones((b,), np.float32),
        "next_state": np.zeros((b, features.STATE_DIM), np.float32),
        "next_options": np.zeros((b, 4, features.OPTION_DIM), np.float32),
        "next_mask": np.zeros((b, 4), bool),
        "done": np.ones((b,), np.float32),  # terminal => target == reward == 1
    }
    return {k: jnp.asarray(v) for k, v in arrs.items()}


def test_update_step_drives_q_toward_reward():
    model = net.QNet(hidden=(32,))
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)
    state = learner.create_train_state(model, params, lr=1e-2)
    step = learner.make_update_step(model, gamma=0.99)
    batch = _toy_batch()
    state, loss0 = step(state, state.params, batch)
    loss = loss0
    for _ in range(80):
        state, loss = step(state, state.params, batch)
    assert np.isfinite(float(loss0)) and np.isfinite(float(loss))
    assert float(loss) < float(loss0)

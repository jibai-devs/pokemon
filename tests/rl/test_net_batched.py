import jax
import jax.numpy as jnp
import numpy as np

from pokemon.rl import features, net


def test_q_values_batched_shape():
    b, k = 4, 6
    model = net.QNet(hidden=(32,))
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)
    states = jnp.zeros((b, features.STATE_DIM))
    options = jnp.zeros((b, k, features.OPTION_DIM))
    q = net.q_values_batched(model, params, states, options)
    assert q.shape == (b, k)
    assert np.all(np.isfinite(np.asarray(q)))

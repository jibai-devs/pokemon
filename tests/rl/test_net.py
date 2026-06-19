import jax
import jax.numpy as jnp
import numpy as np

from pokemon.rl import features, net


def test_qnet_scores_each_option(main_obs):
    state, options, k = features.encode_decision(main_obs)
    model = net.QNet()
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)
    q = net.q_values(model, params, jnp.asarray(state), jnp.asarray(options))
    assert q.shape == (k,)
    assert np.all(np.isfinite(np.asarray(q)))

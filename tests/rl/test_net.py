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


def test_q_values_masked_matches_unpadded(main_obs):
    """The jitted padded scorer matches `q_values` on real slots, -inf on padding."""
    model = net.QNet()
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)

    state, options, k = features.encode_decision(main_obs)
    q_ref = np.asarray(net.q_values(model, params, jnp.asarray(state), jnp.asarray(options)))

    k_max = 64
    state_p, options_p, mask, k_p = features.encode_decision_padded(main_obs, k_max)
    assert k_p == k
    q = np.asarray(
        net.q_values_masked(
            model.apply, params, jnp.asarray(state_p), jnp.asarray(options_p), jnp.asarray(mask)
        )
    )
    assert q.shape == (k_max,)
    np.testing.assert_allclose(q[:k], q_ref, rtol=1e-5, atol=1e-5)
    assert np.all(np.isneginf(q[k:]))  # padding slots are -inf

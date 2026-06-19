import jax
import pytest

from pokemon.rl import eval as ev
from pokemon.rl import features, net, policy


@pytest.mark.slow
def test_evaluate_returns_fraction():
    model = net.QNet(hidden=(32,))
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)
    wr = ev.evaluate(policy.greedy_act(model, params), n_games=2, seed=0)
    assert 0.0 <= wr <= 1.0

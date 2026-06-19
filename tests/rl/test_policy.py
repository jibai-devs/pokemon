import jax
import numpy as np

from pokemon.rl import features, net, policy


def _model_params():
    model = net.QNet(hidden=(32,))
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)
    return model, params


def test_greedy_is_deterministic_and_valid(main_obs):
    model, params = _model_params()
    a1 = policy.select_action(model, params, main_obs, eps=0.0, rng=np.random.default_rng(0))
    a2 = policy.select_action(model, params, main_obs, eps=0.0, rng=np.random.default_rng(7))
    assert a1 == a2  # greedy ignores rng
    assert len(a1) == main_obs["select"]["maxCount"]
    assert all(0 <= i < len(main_obs["select"]["option"]) for i in a1)


def test_eps_one_picks_valid_random(main_obs):
    model, params = _model_params()
    a = policy.select_action(model, params, main_obs, eps=1.0, rng=np.random.default_rng(1))
    assert len(a) == main_obs["select"]["maxCount"]
    assert all(0 <= i < len(main_obs["select"]["option"]) for i in a)


def test_multi_select_returns_distinct_topk():
    obs = {
        "select": {
            "type": 1, "context": 8, "minCount": 2, "maxCount": 2,
            "remainDamageCounter": 0, "remainEnergyCost": 0,
            "option": [{"type": 14}, {"type": 14}, {"type": 14}],
        },
        "current": {"turn": 1, "yourIndex": 0, "players": [{}, {}]},
    }
    model, params = _model_params()
    a = policy.select_action(model, params, obs, eps=0.0, rng=np.random.default_rng(0))
    assert len(a) == 2
    assert len(set(a)) == 2

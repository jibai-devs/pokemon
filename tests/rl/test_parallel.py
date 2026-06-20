import jax
import pytest

from pokemon.rl import features, net, parallel
from pokemon.rl.config import DQNConfig


def test_opponent_name_maps_callables_and_strings():
    from kaggle_environments.envs.cabt.cabt import random_agent

    from pokemon.agent import fire_agent

    assert parallel.opponent_name(random_agent) == "random"
    assert parallel.opponent_name(fire_agent) == "heuristic"
    assert parallel.opponent_name("heuristic") == "heuristic"


def test_resolve_opponent_round_trip():
    assert parallel._resolve_opponent("random").__name__ == "random_agent"
    assert parallel._resolve_opponent("heuristic").__name__ == "fire_agent"
    with pytest.raises(ValueError):
        parallel._resolve_opponent("nope")


@pytest.mark.slow
def test_pool_collects_well_formed_transitions():
    cfg = DQNConfig()
    model = net.QNet(hidden=cfg.hidden)
    params = net.init_params(model, jax.random.PRNGKey(0), features.STATE_DIM, features.OPTION_DIM)
    n = 4
    with parallel.RolloutPool(cfg.hidden, cfg.k_max, n_workers=2) as pool:
        results = pool.collect(params, 0.0, n, "random", list(range(n)), cfg.gamma)
    assert len(results) == n
    for transitions, terminal in results:
        assert terminal in (-1.0, 0.0, 1.0)
        assert len(transitions) > 0
        assert transitions[0]["state"].shape == (features.STATE_DIM,)
        assert transitions[0]["option"].shape == (features.OPTION_DIM,)

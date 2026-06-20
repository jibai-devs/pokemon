import numpy as np
import pytest

from pokemon.rl import features


def test_encode_option_distinguishes_attach_targets():
    """Regression: attach-to-active vs attach-to-a-bench-slot must NOT encode
    identically (the bug that left ~44% of options indistinguishable to the net)."""
    obs = {
        "select": {"type": 0, "context": 0, "maxCount": 1, "option": []},
        "current": {
            "yourIndex": 0,
            "players": [
                {
                    "active": [{"id": 722, "hp": 90, "maxHp": 90, "energies": [2]}],
                    "bench": [{"id": 76, "hp": 70, "maxHp": 70, "energies": []}],
                },
                {},
            ],
        },
    }
    to_active = {"type": 8, "area": 2, "index": 0, "inPlayArea": 4, "inPlayIndex": 0}
    to_bench = {"type": 8, "area": 2, "index": 0, "inPlayArea": 5, "inPlayIndex": 0}
    a = features.encode_option(to_active, obs)
    b = features.encode_option(to_bench, obs)
    assert not np.array_equal(a, b)


@pytest.mark.slow
def test_option_encoding_collision_rate_is_low():
    """Over real games, distinct offered options should rarely encode identically.
    This is the diagnostic for the half-blind-policy bug; keep it well under 5%."""
    import random

    from pokemon.rl import rollout

    total, collisions = 0, 0
    for g in range(12):
        records: list[dict] = []

        def act(obs: dict, _rec=records) -> list[int]:
            _rec.append(obs)
            return random.sample(range(len(obs["select"]["option"])), obs["select"]["maxCount"])

        rollout.play_game(act=act, seed=g)
        for obs in records:
            opts = obs["select"]["option"]
            encs = [tuple(np.round(features.encode_option(o, obs), 4)) for o in opts]
            total += len(opts)
            collisions += len(encs) - len(set(encs))
    rate = collisions / max(total, 1)
    assert rate < 0.05, (
        f"option-encoding collision rate too high: {rate:.1%} ({collisions}/{total})"
    )


def test_encode_option_shape(main_obs):
    opt = main_obs["select"]["option"][0]  # ATTACH
    vec = features.encode_option(opt, main_obs)
    assert vec.shape == (features.OPTION_DIM,)
    assert vec.dtype == np.float32
    assert np.all(np.isfinite(vec))


def test_encode_option_distinguishes_types(main_obs):
    attach = features.encode_option(main_obs["select"]["option"][0], main_obs)
    end = features.encode_option(main_obs["select"]["option"][1], main_obs)
    assert not np.array_equal(attach, end)


def test_encode_decision_stacks_options(main_obs):
    state, options, k = features.encode_decision(main_obs)
    assert state.shape == (features.STATE_DIM,)
    assert options.shape == (2, features.OPTION_DIM)
    assert k == 2

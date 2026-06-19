import numpy as np

from pokemon.rl import features


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

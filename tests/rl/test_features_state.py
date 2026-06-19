import numpy as np

from pokemon.rl import features


def test_encode_state_shape_and_finite(main_obs):
    vec = features.encode_state(main_obs)
    assert vec.shape == (features.STATE_DIM,)
    assert vec.dtype == np.float32
    assert np.all(np.isfinite(vec))


def test_encode_state_is_deterministic(main_obs):
    a = features.encode_state(main_obs)
    b = features.encode_state(main_obs)
    assert np.array_equal(a, b)


def test_encode_state_values_normalized(main_obs):
    vec = features.encode_state(main_obs)
    assert vec.min() >= 0.0 and vec.max() <= 1.0

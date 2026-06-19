import numpy as np

from pokemon.rl.replay import ReplayBuffer


def test_add_and_sample_roundtrip():
    rng = np.random.default_rng(0)
    buf = ReplayBuffer(capacity=10, state_dim=4, option_dim=3, k_max=5)
    s = np.ones(4, np.float32)
    o = np.full(3, 2.0, np.float32)
    next_opts = np.array([[1, 1, 1], [2, 2, 2]], np.float32)  # 2 of 5 slots
    buf.add(s, o, reward=1.5, next_state=s, next_options=next_opts, done=False)
    assert buf.size == 1
    batch = buf.sample(1, rng)
    assert batch["state"].shape == (1, 4)
    assert batch["next_options"].shape == (1, 5, 3)
    assert batch["next_mask"][0].tolist() == [True, True, False, False, False]
    assert abs(float(batch["reward"][0]) - 1.5) < 1e-6


def test_ring_overwrites_when_full():
    buf = ReplayBuffer(capacity=2, state_dim=1, option_dim=1, k_max=1)
    z = np.zeros(1, np.float32)
    for _ in range(5):
        buf.add(z, z, 0.0, z, np.zeros((0, 1), np.float32), True)
    assert buf.size == 2

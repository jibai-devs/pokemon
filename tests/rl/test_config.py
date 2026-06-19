from pokemon.rl.config import DQNConfig


def test_config_defaults_are_sane():
    cfg = DQNConfig()
    assert cfg.gamma == 0.99
    assert cfg.k_max >= 16
    assert cfg.replay_capacity > cfg.batch_size
    assert 0.0 < cfg.lr < 1.0

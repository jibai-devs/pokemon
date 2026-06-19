import dataclasses

from pokemon.rl.config import DQNConfig


def test_eps_decay_default_is_realistic():
    assert DQNConfig().eps_decay_steps <= 50_000


def test_config_is_replaceable():
    cfg = dataclasses.replace(DQNConfig(), eps_decay_steps=10_000, lr=5e-4)
    assert cfg.eps_decay_steps == 10_000
    assert cfg.lr == 5e-4

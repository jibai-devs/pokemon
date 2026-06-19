import pytest

from pokemon.rl import train
from pokemon.rl.config import DQNConfig


@pytest.mark.slow
def test_train_smoke(tmp_path):
    cfg = DQNConfig(batch_size=16, replay_capacity=5000, eps_decay_steps=500, hidden=(32,))
    state, history = train.train(
        cfg,
        iterations=2,
        games_per_iter=2,
        updates_per_iter=5,
        eval_every=1,
        eval_games=1,
        ckpt_dir=str(tmp_path),
        seed=0,
    )
    assert state is not None
    assert len(history) >= 1
    assert all(0.0 <= h["winrate"] <= 1.0 for h in history)
    assert (tmp_path / "params.msgpack").exists()

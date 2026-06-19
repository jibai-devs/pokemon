import numpy as np
import pytest

from pokemon.rl import features, rollout


@pytest.mark.slow
def test_play_game_returns_well_formed_transitions():
    transitions, terminal_reward = rollout.play_game(seed=0)
    assert terminal_reward in (-1.0, 0.0, 1.0)
    assert len(transitions) > 0
    t = transitions[0]
    assert t["state"].shape == (features.STATE_DIM,)
    assert t["option"].shape == (features.OPTION_DIM,)
    assert np.isfinite(t["reward"])
    assert transitions[-1]["done"] is True
    assert transitions[-1]["next_options"].shape[1] == features.OPTION_DIM

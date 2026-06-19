from pokemon.rl import rollout


def test_play_game_uses_supplied_act():
    calls = {"n": 0}

    def always_first(obs):
        calls["n"] += 1
        return [0]

    transitions, terminal_reward = rollout.play_game(act=always_first, seed=0)
    assert calls["n"] > 0
    assert len(transitions) == calls["n"]
    assert terminal_reward in (-1.0, 0.0, 1.0)

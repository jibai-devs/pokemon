from pokemon.rl import reward


def _obs(my_prizes: int, opp_prizes: int, your_index: int = 0):
    players = [None, None]
    players[your_index] = {"prize": [None] * my_prizes}
    players[1 - your_index] = {"prize": [None] * opp_prizes}
    return {"current": {"yourIndex": your_index, "players": players}}


def test_prizes_remaining_reads_my_and_opp():
    obs = _obs(my_prizes=4, opp_prizes=6)
    assert reward.prizes_remaining(obs, 0) == 4
    assert reward.prizes_remaining(obs, 1) == 6


def test_potential_rises_when_i_take_a_prize():
    # Taking one of MY prizes shrinks my pile -> potential increases.
    before = reward.potential(_obs(my_prizes=6, opp_prizes=6))
    after = reward.potential(_obs(my_prizes=5, opp_prizes=6))
    assert after > before


def test_shaped_reward_terminal_adds_win_bonus():
    obs = _obs(my_prizes=1, opp_prizes=3)
    r = reward.shaped_reward(obs, None, gamma=0.99, terminal_reward=1.0)
    # Terminal: gamma*phi(next=0) - phi(s) + terminal.
    expected = -reward.potential(obs) + 1.0
    assert abs(r - expected) < 1e-6

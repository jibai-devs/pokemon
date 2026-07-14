"""Native search binding + end-of-turn expander tests (plan 009 Phases 2-3).

Requires libcg.so (via kaggle_environments cabt env). Tests skip if unavailable.
"""

from __future__ import annotations

import random

import pytest

from pokemon.decks import DRAGAPULT_DECK
from pokemon.determinize import sample_determinization
from pokemon.search_function.turn_search import (
    TurnLine,
    candidate_actions,
    classify_terminal,
    expand_end_of_turn,
    first_action_of_best_line,
    root_player_index,
    score_line,
)

libcg = pytest.importorskip("kaggle_environments.envs.cabt.cg.game")


def _dragapult() -> list[int]:
    return list(DRAGAPULT_DECK)


def _play_to_main(max_steps: int = 80):
    battle_start = libcg.battle_start
    battle_select = libcg.battle_select
    battle_finish = libcg.battle_finish
    deck = _dragapult()
    obs, sd = battle_start(deck, deck)
    assert sd.errorPlayer < 0
    for _ in range(max_steps):
        sel = obs.get("select")
        if not sel:
            battle_finish()
            pytest.skip("no select early")
        if sel.get("type") == 0:  # MAIN
            return obs, battle_finish
        act = list(range(sel["maxCount"]))
        obs = battle_select(act)
        if obs["current"]["result"] >= 0:
            battle_finish()
            pytest.skip("game ended before Main")
    battle_finish()
    pytest.skip("no Main within step budget")


def test_search_begin_and_step_smoke():
    from pokemon.native_search import SearchSession

    obs, finish = _play_to_main()
    try:
        cfg = sample_determinization(obs, _dragapult(), rng=random.Random(0))
        with SearchSession() as s:
            r = s.begin(obs["search_begin_input"], cfg)
            assert r.ok, r.error
            assert r.observation is not None
            assert r.search_id is not None
            opts = r.observation["select"]["option"]
            assert opts
            r2 = s.step(r.search_id, [0])
            assert r2.ok, r2.error
    finally:
        finish()


def test_end_option_flips_to_opponent_eot():
    from pokemon.native_search import SearchSession

    obs, finish = _play_to_main()
    try:
        root = root_player_index(obs)
        cfg = sample_determinization(obs, _dragapult(), rng=random.Random(1))
        with SearchSession() as s:
            r = s.begin(obs["search_begin_input"], cfg)
            assert r.ok
            end_i = next(
                i for i, o in enumerate(r.observation["select"]["option"]) if o.get("type") == 14
            )
            r2 = s.step(r.search_id, [end_i])
            assert r2.ok
            kind = classify_terminal(root, r2.observation)
            assert kind == "eot"
            assert root_player_index(r2.observation) != root
    finally:
        finish()


def test_expand_end_of_turn_finds_eot_line():
    obs, finish = _play_to_main()
    try:
        lines = expand_end_of_turn(
            obs,
            _dragapult(),
            policy="tactical",
            max_nodes=200,
            max_depth=12,
            beam=32,
            rng=random.Random(2),
        )
        assert lines
        kinds = {line.terminal for line in lines}
        assert kinds & {"eot", "win", "loss", "draw", "budget", "depth"}
        # At least one line should take an action.
        assert any(line.actions for line in lines)
        first = first_action_of_best_line(lines, root_player_index(obs))
        assert first is not None
        assert all(isinstance(i, int) for i in first)
    finally:
        finish()


def test_candidate_actions_tactical_includes_end_or_attack():
    obs, finish = _play_to_main()
    try:
        acts = candidate_actions(obs, policy="tactical")
        assert acts
        flat = {i for act in acts for i in act}
        types = {obs["select"]["option"][i]["type"] for i in flat}
        assert types & {13, 14}  # ATTACK or END
    finally:
        finish()


def test_classify_terminal_game_over():
    obs = {"current": {"yourIndex": 0, "result": 0}, "select": {"option": [{"type": 14}], "maxCount": 1}}
    assert classify_terminal(0, obs) == "win"
    assert classify_terminal(1, obs) == "loss"
    obs["current"]["result"] = 2
    assert classify_terminal(0, obs) == "draw"


def test_score_line_prefers_win_and_fewer_prizes():
    win = TurnLine(actions=[[1]], end_obs={"current": {"result": 0, "players": [{"prize": []}, {"prize": [None] * 6}]}}, terminal="win")
    eot_6 = TurnLine(
        actions=[[0]],
        end_obs={"current": {"result": -1, "players": [{"prize": [None] * 6}, {"prize": [None] * 6}]}},
        terminal="eot",
    )
    eot_4 = TurnLine(
        actions=[[2]],
        end_obs={"current": {"result": -1, "players": [{"prize": [None] * 4}, {"prize": [None] * 6}]}},
        terminal="eot",
    )
    assert score_line(win, 0) > score_line(eot_4, 0) > score_line(eot_6, 0)
    assert first_action_of_best_line([eot_6, eot_4, win], 0) == [1]

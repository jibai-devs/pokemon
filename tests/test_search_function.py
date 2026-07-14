"""Unit tests for the engine-backed search decisionmaker's wiring
(``pokemon.search_function``) and its registration as the
``"dragapult_search"`` ruleset -- using synthetic ``obs`` dicts, no
engine/WSL required. ``search``'s early-exit branches (wrong phase, no
search input, no usable deck) never touch the native engine, so they're
covered here; the BFS itself is exercised in ``tests/test_native_search.py``
(skips without ``libcg.so``).
"""

from dataclasses import dataclass

from pokemon.board import _build_ctx
from pokemon.heuristics import RULESETS
from pokemon.heuristics.dragapult import DRAGAPULT_HEURISTICS
from pokemon.search_function import make_turn_bfs_search, search, turn_bfs_search
from pokemon.search_function.turn_search import TurnLine, first_action_of_best_line


@dataclass
class _FakeState:
    my_deck: list[int] | None = None


def _obs(select: dict, search_begin_input: str | None = None) -> dict:
    obs: dict = {
        "select": select,
        "current": {
            "yourIndex": 0,
            "players": [
                {"hand": [], "active": [], "bench": []},
                {"hand": None, "active": [], "bench": []},
            ],
        },
    }
    if search_begin_input is not None:
        obs["search_begin_input"] = search_begin_input
    return obs


def test_dragapult_search_ruleset_tries_bfs_search_first():
    """``turn_bfs_search`` gets first refusal, then the exact same hand-written
    rule stack as the plain ``"dragapult"`` ruleset (same priority order)."""
    ruleset = RULESETS["dragapult_search"]
    assert ruleset.rules[0] is turn_bfs_search
    assert ruleset.rules[1:] == DRAGAPULT_HEURISTICS


def test_dragapult_search_shares_dragapult_state_shape():
    """Both registered rulesets must build the same state shape -- that's
    what makes swapping between them mid-game safe (see
    admin.select_ruleset's docstring caveat)."""
    assert RULESETS["dragapult_search"].init_state is RULESETS["dragapult"].init_state


def test_dragapult_opening_ruleset_tries_bfs_search_first():
    ruleset = RULESETS["dragapult_opening"]
    assert ruleset.rules[1:] == DRAGAPULT_HEURISTICS
    assert ruleset.rules[0] is not turn_bfs_search  # its own scorer, not the default one
    assert ruleset.init_state is RULESETS["dragapult"].init_state
    select = {"type": 9, "context": 42, "maxCount": 1, "option": []}  # not Main
    ctx = _build_ctx(_obs(select, search_begin_input="blob"), _FakeState(my_deck=[1] * 60))
    assert ruleset.rules[0](ctx) is None  # early-exit still works regardless of scorer


def test_dragapult_smarter_search_ruleset_tries_bfs_search_first():
    ruleset = RULESETS["dragapult_smarter_search"]
    assert ruleset.rules[0] is not turn_bfs_search  # its own scorer, not the default one
    assert ruleset.rules[1:] == DRAGAPULT_HEURISTICS
    assert ruleset.init_state is RULESETS["dragapult"].init_state


def test_turn_bfs_search_defers_off_main_phase():
    select = {"type": 9, "context": 42, "maxCount": 1, "option": []}  # not Main
    ctx = _build_ctx(_obs(select, search_begin_input="blob"), _FakeState(my_deck=[1] * 60))
    assert turn_bfs_search(ctx) is None


def test_turn_bfs_search_defers_without_search_begin_input():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": []}  # Main
    ctx = _build_ctx(_obs(select), _FakeState(my_deck=[1] * 60))
    assert turn_bfs_search(ctx) is None


def test_turn_bfs_search_defers_without_my_deck():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": []}
    ctx = _build_ctx(_obs(select, search_begin_input="blob"), _FakeState())
    assert turn_bfs_search(ctx) is None


def test_turn_bfs_search_defers_when_my_deck_wrong_length():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": []}
    ctx = _build_ctx(_obs(select, search_begin_input="blob"), _FakeState(my_deck=[1, 2, 3]))
    assert turn_bfs_search(ctx) is None


def test_turn_bfs_search_defers_on_a_state_object_with_no_my_deck_attribute():
    """A ruleset's state that never declares ``my_deck`` at all (not just
    ``None``) must degrade the same way -- ``getattr`` is what makes this
    module usable by any future ruleset's state, not just Dragapult's."""
    select = {"type": 0, "context": 0, "maxCount": 1, "option": []}
    ctx = _build_ctx(_obs(select, search_begin_input="blob"), state=object())
    assert turn_bfs_search(ctx) is None


def test_search_is_callable_directly_without_any_ruleset_registration():
    """The whole point of ``search`` (as opposed to ``turn_bfs_search``):
    any decisionmaking engine can call it inline with just a ``ctx`` and a
    scorer, no ``Ruleset``/``RULESETS`` involvement at all."""
    select = {"type": 9, "context": 42, "maxCount": 1, "option": []}  # not Main
    ctx = _build_ctx(_obs(select, search_begin_input="blob"), _FakeState(my_deck=[1] * 60))
    assert search(ctx, lambda line, root: (0,)) is None


def test_turn_bfs_search_and_search_agree_on_the_default_objective():
    """``turn_bfs_search`` is just ``make_turn_bfs_search()`` --
    ``search(ctx, score_line)`` with the budget defaults curried in. Same
    early-exit result either way."""
    select = {"type": 0, "context": 0, "maxCount": 1, "option": []}  # Main, but no search_begin_input
    ctx = _build_ctx(_obs(select), _FakeState(my_deck=[1] * 60))
    assert turn_bfs_search(ctx) == search(ctx)


def test_make_turn_bfs_search_builds_an_independently_working_rule():
    """A custom-scored rule built via the factory must still be a normal
    Heuristic -- same early-exit behavior as the default ``turn_bfs_search``
    instance, just with a different (here, trivial) objective."""
    custom_rule = make_turn_bfs_search(score_fn=lambda line, root: (0,))
    select = {"type": 9, "context": 42, "maxCount": 1, "option": []}  # not Main
    ctx = _build_ctx(_obs(select, search_begin_input="blob"), _FakeState(my_deck=[1] * 60))
    assert custom_rule(ctx) is None


def _end_obs(my_prizes: int, opp_hp: int, opp_max_hp: int) -> dict:
    """A minimal end-of-line observation: our own remaining prize count and
    the opponent's Active HP -- exactly what score_line/a damage-only
    scorer each look at."""
    return {
        "current": {
            "players": [
                {"prize": [None] * my_prizes},
                {"prize": [None] * 6, "active": [{"hp": opp_hp, "maxHp": opp_max_hp}]},
            ],
        }
    }


def _damage_only_score(line: TurnLine, root_player: int) -> tuple:
    """A custom objective that ignores prizes entirely -- purely 'how much
    damage did we deal to the opponent's Active'."""
    if line.end_obs is None:
        return (0,)
    players = (line.end_obs.get("current") or {}).get("players") or []
    opp_idx = 1 - root_player
    opp = players[opp_idx] if len(players) > opp_idx else {}
    active = (opp.get("active") or [None])[0] or {}
    hp, max_hp = active.get("hp"), active.get("maxHp")
    if hp is None or max_hp is None:
        return (0,)
    return (int(max_hp) - int(hp),)


def test_custom_score_fn_changes_which_line_wins():
    """Proves scoring is genuinely pluggable, not just parameterized in
    name: the built-in ``score_line`` ranks own-prizes-taken above opponent
    damage dealt, so it prefers the prize-taking line here even though it
    deals far less damage -- a custom score_fn that only looks at damage
    picks the other line instead."""
    heavy_damage = TurnLine(
        actions=[[0]],
        end_obs=_end_obs(my_prizes=6, opp_hp=10, opp_max_hp=200),  # no prize taken, 190 dmg
        terminal="eot",
    )
    took_prize = TurnLine(
        actions=[[1]],
        end_obs=_end_obs(my_prizes=5, opp_hp=150, opp_max_hp=200),  # 1 prize taken, 50 dmg
        terminal="eot",
    )
    lines = [heavy_damage, took_prize]

    assert first_action_of_best_line(lines, root_player=0) == [1]  # default: prize-taking wins
    assert first_action_of_best_line(lines, root_player=0, score_fn=_damage_only_score) == [0]  # custom: damage wins

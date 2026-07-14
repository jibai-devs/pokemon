"""Unit tests for admin.py's ruleset-selection logic -- synthetic ``obs``
dicts, no engine/WSL required.
"""

from pokemon.admin import _is_own_first_turn, select_ruleset
from pokemon.heuristics import RULESETS


def _obs(turn: int, your_index: int = 0, first_player: int | None = None) -> dict:
    current: dict = {"turn": turn, "yourIndex": your_index}
    if first_player is not None:
        current["firstPlayer"] = first_player
    return {"current": current}


def test_is_own_first_turn_true_on_turn_1_going_first():
    assert _is_own_first_turn(_obs(turn=1, your_index=0, first_player=0)) is True


def test_is_own_first_turn_true_on_turn_2_going_second():
    assert _is_own_first_turn(_obs(turn=2, your_index=0, first_player=1)) is True


def test_is_own_first_turn_false_on_turn_1_going_second():
    """Turn 1 is the opponent's opening turn if they went first -- not ours."""
    assert _is_own_first_turn(_obs(turn=1, your_index=0, first_player=1)) is False


def test_is_own_first_turn_false_on_turn_2_going_first():
    """Turn 2 is the opponent's opening turn if we went first -- not ours either."""
    assert _is_own_first_turn(_obs(turn=2, your_index=0, first_player=0)) is False


def test_is_own_first_turn_false_on_later_turns():
    assert _is_own_first_turn(_obs(turn=3, your_index=0, first_player=0)) is False
    assert _is_own_first_turn(_obs(turn=4, your_index=0, first_player=1)) is False


def test_is_own_first_turn_defaults_to_going_first_when_undetermined():
    """``firstPlayer`` absent entirely -> treated as "assume going first" per
    ``_build_ctx``'s own convention -- never crashes on a missing key."""
    assert _is_own_first_turn(_obs(turn=1, your_index=0)) is True
    assert _is_own_first_turn(_obs(turn=2, your_index=0)) is False


def test_select_ruleset_prefers_opening_on_our_first_turn():
    obs = _obs(turn=1, your_index=0, first_player=0)
    assert select_ruleset(obs, "dragapult") is RULESETS["dragapult_opening"]


def test_select_ruleset_prefers_opening_on_our_first_turn_going_second():
    obs = _obs(turn=2, your_index=0, first_player=1)
    assert select_ruleset(obs, "dragapult") is RULESETS["dragapult_opening"]


def test_select_ruleset_prefers_smarter_search_otherwise():
    obs = _obs(turn=5, your_index=0, first_player=0)
    assert select_ruleset(obs, "dragapult") is RULESETS["dragapult_smarter_search"]

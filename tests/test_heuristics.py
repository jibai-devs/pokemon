"""Unit tests for the heuristic-agent framework, using synthetic ``obs``
dicts — without needing the real engine (WSL/libcg.so).

``_build_ctx`` lives in ``pokemon.board``; the dispatch loop that runs a
ruleset's rules and falls back to random lives in ``pokemon.admin``.

Deck-specific heuristics should get their own tests alongside their
functions in ``pokemon.heuristics.dragapult``, following the pattern below:
build a minimal ``obs`` via ``_obs``, run it through ``_build_ctx``, and
assert the heuristic returns the expected option indices (or ``None``).
"""

from dataclasses import dataclass

from pokemon.admin import _build_agent_for_ruleset, _init_state
from pokemon.board import _build_ctx
from pokemon.heuristics import Ruleset


def _obs(select: dict, hand: list | None = None, active: list | None = None, bench: list | None = None):
    return {
        "select": select,
        "current": {
            "yourIndex": 0,
            "players": [
                {"hand": hand or [], "active": active or [], "bench": bench or []},
                {"hand": None, "active": [], "bench": []},
            ],
        },
    }


def _empty_ruleset() -> Ruleset:
    return Ruleset(rules=[], init_state=dict)


def test_build_ctx_resolves_hand_and_active():
    hand = [{"id": 1}]
    active = [{"id": 2}]
    select = {"type": 0, "context": 0, "maxCount": 1, "option": []}
    ctx = _build_ctx(_obs(select, hand=hand, active=active), {})
    assert ctx.hand == hand
    assert ctx.me["active"] == active


def test_build_agent_falls_back_to_random_with_no_heuristics():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}, {"type": 12}]}
    agent = _build_agent_for_ruleset(deck=[], ruleset=_empty_ruleset())
    chosen = agent(_obs(select))
    assert chosen and 0 <= chosen[0] < 2


def test_build_agent_submits_deck_on_setup():
    deck = [1, 2, 3]
    agent = _build_agent_for_ruleset(deck=deck, ruleset=_empty_ruleset())
    assert agent({"select": None}) == deck


@dataclass
class _StateWithDeck:
    my_deck: list[int] | None = None


def test_init_state_seeds_my_deck_when_state_supports_it():
    ruleset = Ruleset(rules=[], init_state=_StateWithDeck)
    state = _init_state(ruleset, deck=[1, 2, 3])
    assert state.my_deck == [1, 2, 3]


def test_init_state_ignores_deck_when_state_has_no_my_deck_field():
    """A plain dict (no attributes) must not crash -- ``_init_state`` uses
    ``hasattr`` so it's a no-op for any ruleset whose state doesn't declare
    ``my_deck``, not just ``DragapultState``."""
    state = _init_state(_empty_ruleset(), deck=[1, 2, 3])
    assert state == {}

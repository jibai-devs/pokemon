"""Unit tests for the heuristic-agent framework, using synthetic ``obs``
dicts — without needing the real engine (WSL/libcg.so).

Deck-specific heuristics should get their own tests alongside their
functions in ``pokemon.heuristics``, following the pattern below: build a
minimal ``obs`` via ``_obs``, run it through ``_build_ctx``, and assert the
heuristic returns the expected option indices (or ``None``).
"""

from pokemon.heuristics import _build_ctx, make_heuristic_agent


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


def test_build_ctx_resolves_hand_and_active():
    hand = [{"id": 1}]
    active = [{"id": 2}]
    select = {"type": 0, "context": 0, "maxCount": 1, "option": []}
    ctx = _build_ctx(_obs(select, hand=hand, active=active), {})
    assert ctx.hand == hand
    assert ctx.me["active"] == active


def test_make_heuristic_agent_falls_back_to_random_with_no_heuristics():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}, {"type": 12}]}
    agent = make_heuristic_agent(deck=[], heuristics=[])
    chosen = agent(_obs(select))
    assert chosen and 0 <= chosen[0] < 2


def test_make_heuristic_agent_submits_deck_on_setup():
    deck = [1, 2, 3]
    agent = make_heuristic_agent(deck=deck, heuristics=[])
    assert agent({"select": None}) == deck

"""Unit tests for `pokemon.determinize` (docs/plans/009_native_search_plan.md Phase 1).

Validates the sampler both on synthetic ``obs`` (exact composition
invariants) and on real captured game logs under ``heuristic_loop/logs/``
(structural sanity only — those snapshots include the mid-step transient
off-by-one noise the module docstring calls out, so real-log assertions stay
loose: right shapes, right totals, no crash).
"""

import glob
import json
import random
from collections import Counter

import pytest

from pokemon.decks import DRAGAPULT_DECK
from pokemon.determinize import sample_determinization

RNG = random.Random(0)


def _obs(me: dict, opp: dict, deck_count: int, prize_len: int):
    return {
        "current": {
            "yourIndex": 0,
            "players": [
                {"deckCount": deck_count, "prize": [None] * prize_len, **me},
                opp,
            ],
        }
    }


def test_own_split_uses_exact_known_composition():
    deck = [1, 1, 2, 3]
    me = {"hand": [{"id": 1}], "discard": [], "active": [], "bench": []}
    opp = {
        "deckCount": 0,
        "prize": [],
        "handCount": 0,
        "hand": None,
        "discard": [],
        "active": [],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=2, prize_len=1)
    cfg = sample_determinization(obs, deck, rng=RNG)
    assert Counter(cfg["myDeck"] + cfg["myPrize"]) == Counter([1, 2, 3])
    assert len(cfg["myDeck"]) == 2
    assert len(cfg["myPrize"]) == 1


def test_own_split_clips_negative_counts_from_transient_overcounts():
    # "seen" claims more copies of id 1 than the deck actually has —
    # shouldn't raise or go negative, just clip to zero remaining.
    deck = [1, 2, 3]
    me = {
        "hand": [{"id": 1}],
        "discard": [{"id": 1}],
        "active": [{"id": 1, "energyCards": [], "tools": [], "preEvolution": []}],
        "bench": [],
    }
    opp = {
        "deckCount": 0,
        "prize": [],
        "handCount": 0,
        "hand": None,
        "discard": [],
        "active": [],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=1, prize_len=1)
    cfg = sample_determinization(obs, deck, rng=RNG)
    assert 1 not in cfg["myDeck"] and 1 not in cfg["myPrize"]
    assert Counter(cfg["myDeck"] + cfg["myPrize"]) == Counter([2, 3])


def test_own_split_uses_known_prize_ids_when_given():
    """A ruleset's own prize deduction (e.g. prize_check's deck_memory)
    should land those specific ids in myPrize instead of an arbitrary
    random split."""
    deck = [1, 1, 2, 3]
    me = {"hand": [], "discard": [], "active": [], "bench": []}
    opp = {
        "deckCount": 0,
        "prize": [],
        "handCount": 0,
        "hand": None,
        "discard": [],
        "active": [],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=3, prize_len=1)
    cfg = sample_determinization(obs, deck, rng=RNG, known_prize_ids=[2])
    assert cfg["myPrize"] == [2]
    assert Counter(cfg["myDeck"]) == Counter([1, 1, 3])


def test_own_split_pads_incomplete_known_prize_ids_with_a_random_guess():
    """Only 1 of 2 remaining prizes deduced -- the rest still needs to be
    filled in, just from whatever's left over after removing the known one."""
    deck = [1, 1, 2, 3]
    me = {"hand": [], "discard": [], "active": [], "bench": []}
    opp = {
        "deckCount": 0,
        "prize": [],
        "handCount": 0,
        "hand": None,
        "discard": [],
        "active": [],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=2, prize_len=2)
    cfg = sample_determinization(obs, deck, rng=RNG, known_prize_ids=[2])
    assert 2 in cfg["myPrize"]
    assert len(cfg["myPrize"]) == 2
    assert Counter(cfg["myPrize"] + cfg["myDeck"]) == Counter([1, 1, 2, 3])


def test_own_split_ignores_known_prize_ids_the_unseen_pool_cant_back_up():
    """A stale/wrong deduction (a card id not actually unseen, e.g. already
    visible or not even in the deck) must degrade to a random guess for
    that slot rather than overcounting or crashing."""
    deck = [1, 1, 2, 3]
    me = {"hand": [], "discard": [], "active": [], "bench": []}
    opp = {
        "deckCount": 0,
        "prize": [],
        "handCount": 0,
        "hand": None,
        "discard": [],
        "active": [],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=3, prize_len=1)
    cfg = sample_determinization(obs, deck, rng=RNG, known_prize_ids=[99])
    assert 99 not in cfg["myPrize"]
    assert len(cfg["myPrize"]) == 1
    assert Counter(cfg["myPrize"] + cfg["myDeck"]) == Counter([1, 1, 2, 3])


def test_opponent_falls_back_to_filler_before_anything_revealed():
    deck = DRAGAPULT_DECK
    me = {"hand": [], "discard": [], "active": [], "bench": []}
    opp = {
        "deckCount": 53,
        "prize": [None] * 6,
        "handCount": 7,
        "hand": None,
        "discard": [],
        "active": [{"id": 500, "energyCards": [], "tools": [], "preEvolution": []}],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=60, prize_len=6)
    cfg = sample_determinization(obs, deck, rng=RNG)
    assert len(cfg["enemyDeck"]) == 53
    assert len(cfg["enemyPrize"]) == 6
    assert len(cfg["enemyHand"]) == 7
    assert cfg["enemyActive"] == []  # visible active -> not guessed
    assert set(cfg["enemyDeck"] + cfg["enemyPrize"] + cfg["enemyHand"]) == {500}


def test_opponent_active_guessed_only_when_hidden():
    deck = DRAGAPULT_DECK
    me = {"hand": [], "discard": [], "active": [], "bench": []}
    opp = {
        "deckCount": 59,
        "prize": [None] * 6,
        "handCount": 6,
        "hand": None,
        "discard": [],
        "active": [],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=60, prize_len=6)
    cfg = sample_determinization(obs, deck, rng=RNG)
    assert len(cfg["enemyActive"]) == 1


def test_opponent_resamples_from_revealed_cards():
    deck = DRAGAPULT_DECK
    me = {"hand": [], "discard": [], "active": [], "bench": []}
    opp = {
        "deckCount": 50,
        "prize": [None] * 6,
        "handCount": 3,
        "hand": None,
        "discard": [{"id": 999}],
        "active": [{"id": 999, "energyCards": [], "tools": [], "preEvolution": []}],
        "bench": [],
    }
    obs = _obs(me, opp, deck_count=60, prize_len=6)
    cfg = sample_determinization(obs, deck, rng=RNG)
    assert set(cfg["enemyDeck"] + cfg["enemyPrize"] + cfg["enemyHand"]) == {999}
    assert cfg["enemyActive"] == []  # active is visible here, not hidden


@pytest.mark.parametrize("path", glob.glob("heuristic_loop/logs/**/*.json", recursive=True)[:5])
def test_real_captured_logs_produce_well_shaped_config(path):
    game = json.load(open(path, encoding="utf-8"))
    steps = game["steps"]
    deck = next(s[0]["action"] for s in steps if len(s[0]["action"]) == 60)

    checked = 0
    for step in steps:
        obs = step[0]["observation"]
        current = obs.get("current")
        if not current:
            continue
        my_idx = current.get("yourIndex", 0)
        players = current["players"]
        me, opp = players[my_idx], players[1 - my_idx]

        cfg = sample_determinization(obs, deck, rng=RNG)

        # Own deck/prize total is clipped against transient off-by-one noise
        # in a captured mid-step obs (a card momentarily counted in two
        # zones in the same frame) -- see module docstring -- so check the
        # combined total is close, not that the prize/deck split is exact.
        assert (
            abs(
                len(cfg["myPrize"])
                + len(cfg["myDeck"])
                - (len(me.get("prize") or []) + me.get("deckCount", 0))
            )
            <= 5
        )
        assert len(cfg["enemyPrize"]) == len(opp.get("prize") or [])
        assert len(cfg["enemyDeck"]) == opp.get("deckCount", 0)
        expected_hand = opp.get("handCount", 0) if opp.get("hand") is None else 0
        assert len(cfg["enemyHand"]) == expected_hand
        checked += 1

    assert checked > 0

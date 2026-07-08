"""Unit tests for the Dragapult ex deck-specific heuristics (PKM-017/007),
using synthetic ``obs`` dicts — no engine/WSL required. Follows the pattern
in ``test_heuristics.py``.
"""

from pokemon.heuristics import _build_ctx
from pokemon.heuristics_dragapult import (
    BOSS_ORDERS,
    BUDDY_BUDDY_POFFIN,
    DRAGAPULT_EX,
    DRAKLOAK,
    DREEPY,
    FIRE_ENERGY,
    LILLIES_DETERMINATION,
    MEOWTH_EX,
    WATCHTOWER,
    active_replacement,
    archetype_latch,
    attack_choice,
    boss_orders_target,
    discard_sequencing,
    mulligan,
    supporter_tiebreak,
    watchtower_meowth_sequencing,
)


def _obs(
    select: dict,
    hand: list | None = None,
    active: list | None = None,
    bench: list | None = None,
    opp_active: list | None = None,
    opp_bench: list | None = None,
    opp_discard: list | None = None,
    stadium: list | None = None,
    turn: int = 1,
):
    return {
        "select": select,
        "current": {
            "yourIndex": 0,
            "turn": turn,
            "stadium": stadium or [],
            "players": [
                {"hand": hand or [], "active": active or [], "bench": bench or []},
                {
                    "hand": None,
                    "active": opp_active or [],
                    "bench": opp_bench or [],
                    "discard": opp_discard or [],
                },
            ],
        },
    }


def _ctx(*args, state=None, **kwargs):
    return _build_ctx(_obs(*args, **kwargs), state if state is not None else {})


def test_mulligan_yes_when_no_basics_in_hand():
    select = {"type": 9, "context": 42, "maxCount": 1, "option": [{"type": 1}, {"type": 2}]}
    ctx = _ctx(select, hand=[{"id": LILLIES_DETERMINATION}])
    assert mulligan(ctx) == [0]  # YES is option 0


def test_mulligan_no_when_basic_present():
    select = {"type": 9, "context": 42, "maxCount": 1, "option": [{"type": 1}, {"type": 2}]}
    ctx = _ctx(select, hand=[{"id": DREEPY}])
    assert mulligan(ctx) == [1]  # NO is option 1


def test_active_replacement_prefers_ready_dragapult_over_drakloak():
    bench = [
        {"id": DRAKLOAK, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 1},
        {
            "id": DRAGAPULT_EX,
            "hp": 320,
            "maxHp": 320,
            "energyCards": [{"id": FIRE_ENERGY}],
            "serial": 2,
        },
    ]
    select = {
        "type": 1,
        "context": 4,  # TO_ACTIVE
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0},
            {"type": 3, "area": 5, "index": 1},
        ],
    }
    ctx = _ctx(select, bench=bench)
    assert active_replacement(ctx) == [1]


def test_discard_sequencing_prefers_dupe_trainer_over_attacker_line():
    hand = [{"id": BUDDY_BUDDY_POFFIN}, {"id": DREEPY}]
    select = {
        "type": 1,
        "context": 8,  # DISCARD
        "maxCount": 1,
        "option": [
            {"type": 11, "area": 2, "index": 0},
            {"type": 11, "area": 2, "index": 1},
        ],
    }
    ctx = _ctx(select, hand=hand)
    assert discard_sequencing(ctx) == [0]


def test_attack_choice_avoids_ex_attack_vs_crustle():
    active = {
        "id": DRAGAPULT_EX,
        "hp": 320,
        "maxHp": 320,
        "energyCards": [{"id": FIRE_ENERGY}],
    }
    select = {
        "type": 6,
        "context": 35,  # ATTACK
        "maxCount": 1,
        "option": [
            {"type": 13, "attackId": 154},  # Phantom Dive (ex attack)
            {"type": 13, "attackId": 153},  # Jet Headbutt (non-ex)
        ],
    }
    ctx = _ctx(select, active=[active], opp_active=[{"id": 345, "name": "Crustle", "hp": 130, "maxHp": 130}])
    assert attack_choice(ctx) == [1]


def test_attack_choice_prefers_highest_damage_when_unblocked():
    active = {"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}
    select = {
        "type": 6,
        "context": 35,
        "maxCount": 1,
        "option": [
            {"type": 13, "attackId": 154},  # Phantom Dive, 200 dmg
            {"type": 13, "attackId": 153},  # Jet Headbutt, 70 dmg
        ],
    }
    ctx = _ctx(select, active=[active], opp_active=[{"id": 1, "name": "Something Else", "hp": 100, "maxHp": 100}])
    assert attack_choice(ctx) == [0]


def test_watchtower_deferred_while_meowth_ex_unsearched():
    hand = [{"id": WATCHTOWER}, {"id": MEOWTH_EX}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 7, "index": 0},  # PLAY Watchtower
            {"type": 7, "index": 1},  # PLAY Meowth ex
        ],
    }
    ctx = _ctx(select, hand=hand)
    assert watchtower_meowth_sequencing(ctx) == [1]


def test_supporter_tiebreak_defaults_to_lillies_determination():
    hand = [{"id": BOSS_ORDERS}, {"id": LILLIES_DETERMINATION}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 7, "index": 0},
            {"type": 7, "index": 1},
        ],
    }
    ctx = _ctx(select, hand=hand, active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}])
    # No lethal payoff available for Boss's Orders (opp bench is empty) -> falls to Lillie's Determination
    assert supporter_tiebreak(ctx) == [1]


def test_archetype_latch_and_boss_orders_targets_meganium_over_arboliva_ex():
    opp_bench = [
        {"id": 404, "name": "Arboliva ex", "hp": 300, "maxHp": 310},
        {"id": 710, "name": "Meganium", "hp": 160, "maxHp": 160},
    ]
    select = {
        "type": 1,
        "context": 3,  # SWITCH
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0},
            {"type": 3, "area": 5, "index": 1},
        ],
    }
    state: dict = {}
    ctx = _ctx(select, opp_bench=opp_bench, state=state)
    archetype_latch(ctx)
    assert state["archetype"] == "arboliva"
    assert boss_orders_target(ctx) == [1]  # Meganium, per Section 8's priority-target note

"""Unit tests for the Dragapult ex deck-specific heuristics (PKM-017/007),
using synthetic ``obs`` dicts — no engine/WSL required. Follows the pattern
in ``test_heuristics.py``.
"""

from pokemon.heuristics import _build_ctx
from pokemon.heuristics_dragapult import (
    BOSS_ORDERS,
    BUDDY_BUDDY_POFFIN,
    BUDEW,
    DRAGAPULT_EX,
    DRAKLOAK,
    DREEPY,
    FIRE_ENERGY,
    LILLIES_DETERMINATION,
    MEOWTH_EX,
    MUNKIDORI,
    NIGHT_STRETCHER,
    POKE_PAD,
    PSYCHIC_ENERGY,
    WATCHTOWER,
    active_replacement,
    archetype_latch,
    attach_energy,
    attack_choice,
    boss_orders_target,
    discard_sequencing,
    evolve_choice,
    mulligan,
    play_search_for_dreepy,
    search_for_dreepy,
    supporter_tiebreak,
    watchtower_meowth_sequencing,
)


def _obs(
    select: dict,
    hand: list | None = None,
    active: list | None = None,
    bench: list | None = None,
    discard: list | None = None,
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
                {"hand": hand or [], "active": active or [], "bench": bench or [], "discard": discard or []},
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


def test_discard_sequencing_fires_when_options_typed_card_not_discard():
    """Regression for PKM-019: real replays type discard options as generic
    OptionType.CARD (3), never OptionType.DISCARD (11) -- the function must
    key off sel_context alone, not option.type."""
    hand = [{"id": BUDDY_BUDDY_POFFIN}, {"id": DREEPY}]
    select = {
        "type": 1,
        "context": 8,  # DISCARD
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 2, "index": 0},
            {"type": 3, "area": 2, "index": 1},
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


def test_boss_orders_target_voluntary_retreat_uses_own_board_tiering():
    """Regression for PKM-019: a plain SWITCH decision that resolves to OUR
    OWN bench (voluntary retreat) used to be evaluated against the
    opponent's board instead, silently dropping/misassigning candidates
    whenever the two benches differed in size. Options carry an explicit
    playerIndex identifying whose board they're on."""
    bench = [
        {"id": MUNKIDORI, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 1},
        {
            "id": DRAGAPULT_EX,
            "hp": 320,
            "maxHp": 320,
            "energyCards": [{"id": FIRE_ENERGY}, {"id": PSYCHIC_ENERGY}],
            "serial": 2,
        },
    ]
    select = {
        "type": 1,
        "context": 3,  # SWITCH (voluntary retreat, not a forced TO_ACTIVE)
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0, "playerIndex": 0},
            {"type": 3, "area": 5, "index": 1, "playerIndex": 0},
        ],
    }
    # opponent's bench only has one card -- the old bug indexed into this
    # instead of ours, so a correct fix must not be fooled by it.
    ctx = _ctx(select, bench=bench, opp_bench=[{"id": 1, "name": "Staryu", "hp": 60, "maxHp": 60}])
    assert boss_orders_target(ctx) == [1]  # ready Dragapult ex, per _own_board_tier


def test_boss_orders_target_still_targets_opponent_with_explicit_player_index():
    opp_bench = [
        {"id": 404, "name": "Arboliva ex", "hp": 300, "maxHp": 310},
        {"id": 710, "name": "Meganium", "hp": 160, "maxHp": 160},
    ]
    select = {
        "type": 1,
        "context": 3,  # SWITCH (Boss's Orders)
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0, "playerIndex": 1},
            {"type": 3, "area": 5, "index": 1, "playerIndex": 1},
        ],
    }
    state: dict = {}
    ctx = _ctx(select, opp_bench=opp_bench, state=state)
    archetype_latch(ctx)
    assert state["archetype"] == "arboliva"
    assert boss_orders_target(ctx) == [1]  # Meganium, per Section 8's priority-target note


def test_play_search_for_dreepy_prefers_poke_pad_when_stalled():
    hand = [{"id": POKE_PAD}, {"id": BOSS_ORDERS}]
    select = {
        "type": 0,
        "context": 0,  # MAIN
        "maxCount": 1,
        "option": [
            {"index": 0, "type": 7},  # PLAY Poke Pad
            {"index": 1, "type": 7},  # PLAY Boss's Orders
            {"type": 14},  # End
        ],
    }
    ctx = _ctx(select, hand=hand, active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}])
    assert play_search_for_dreepy(ctx) == [0]


def test_play_search_for_dreepy_defers_when_dreepy_not_stalled():
    hand = [{"id": POKE_PAD}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [{"index": 0, "type": 7}, {"type": 14}],
    }
    ctx = _ctx(select, hand=hand, active=[{"id": DREEPY, "hp": 70, "maxHp": 70, "energyCards": []}])
    assert play_search_for_dreepy(ctx) is None


def test_search_for_dreepy_picks_dreepy_from_poke_pad_deck_search():
    select = {
        "type": 1,
        "context": 7,  # TO_HAND
        "maxCount": 1,
        "effect": {"id": POKE_PAD, "playerIndex": 0},
        "deck": [
            {"id": MUNKIDORI},
            {"id": DREEPY},
            {"id": BUDEW},
        ],
        "option": [
            {"type": 3, "area": 1, "index": 0},
            {"type": 3, "area": 1, "index": 1},
            {"type": 3, "area": 1, "index": 2},
        ],
    }
    ctx = _ctx(select, active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}])
    assert search_for_dreepy(ctx) == [1]


def test_search_for_dreepy_picks_dreepy_from_night_stretcher_discard():
    discard = [{"id": MUNKIDORI}, {"id": PSYCHIC_ENERGY}, {"id": DREEPY}]
    select = {
        "type": 1,
        "context": 7,  # TO_HAND
        "maxCount": 1,
        "effect": {"id": NIGHT_STRETCHER, "playerIndex": 0},
        "option": [
            {"type": 3, "area": 3, "index": 0},
            {"type": 3, "area": 3, "index": 1},
            {"type": 3, "area": 3, "index": 2},
        ],
    }
    ctx = _ctx(select, discard=discard, active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}])
    assert search_for_dreepy(ctx) == [2]


def test_search_for_dreepy_defers_for_unrelated_effect():
    select = {
        "type": 1,
        "context": 7,
        "maxCount": 1,
        "effect": {"id": BOSS_ORDERS, "playerIndex": 0},
        "deck": [{"id": DREEPY}],
        "option": [{"type": 3, "area": 1, "index": 0}],
    }
    ctx = _ctx(select, active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}])
    assert search_for_dreepy(ctx) is None


def test_evolve_choice_prefers_evolve_over_non_lethal_attack():
    active = {"id": DREEPY, "hp": 70, "maxHp": 70, "energyCards": [{"id": PSYCHIC_ENERGY}]}
    select = {
        "type": 0,
        "context": 0,  # MAIN
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 4, "inPlayIndex": 0, "type": 9},  # EVOLVE Drakloak
            {"attackId": 150, "type": 13},  # Petty Grudge, 10 dmg
            {"type": 14},  # End
        ],
    }
    ctx = _ctx(select, hand=[{"id": DRAKLOAK}], active=[active], opp_active=[{"id": 1, "hp": 200, "maxHp": 200}])
    assert evolve_choice(ctx) == [0]


def test_evolve_choice_defers_when_attack_is_lethal():
    active = {"id": DREEPY, "hp": 70, "maxHp": 70, "energyCards": [{"id": FIRE_ENERGY}, {"id": PSYCHIC_ENERGY}]}
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 4, "inPlayIndex": 0, "type": 9},  # EVOLVE Drakloak
            {"attackId": 151, "type": 13},  # Bite, 40 dmg
            {"type": 14},
        ],
    }
    ctx = _ctx(select, hand=[{"id": DRAKLOAK}], active=[active], opp_active=[{"id": 1, "hp": 40, "maxHp": 40}])
    assert evolve_choice(ctx) is None


def test_attach_energy_targets_munkidori_for_mind_bend_fuel():
    munkidori = {"id": MUNKIDORI, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 1}
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 0, "type": 8},  # ATTACH Psychic -> Munkidori
        ],
    }
    ctx = _ctx(select, hand=[{"id": PSYCHIC_ENERGY}], bench=[munkidori])
    assert attach_energy(ctx) == [0]


def test_attach_energy_falls_back_to_budew_when_no_attacker_line_target():
    budew = {"id": BUDEW, "hp": 30, "maxHp": 30, "energyCards": [], "serial": 1}
    munkidori = {"id": MUNKIDORI, "hp": 90, "maxHp": 90, "energyCards": [{"id": PSYCHIC_ENERGY}], "serial": 2}
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 0, "type": 8},  # ATTACH Fire -> Budew
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 1, "type": 8},  # ATTACH Fire -> Munkidori
        ],
    }
    ctx = _ctx(select, hand=[{"id": FIRE_ENERGY}], bench=[budew, munkidori])
    # Munkidori (already has a real payoff target) outranks Budew (free attack, no fuel need)
    assert attach_energy(ctx) == [1]

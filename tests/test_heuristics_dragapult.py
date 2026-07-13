"""Unit tests for the Dragapult ex deck-specific heuristics (PKM-017/007),
using synthetic ``obs`` dicts — no engine/WSL required. Follows the pattern
in ``test_heuristics.py``.
"""

from pokemon.board import _build_ctx
from pokemon.deck_id import DeckIdentifier
from pokemon.heuristics.dragapult import (
    BOSS_ORDERS,
    BUDDY_BUDDY_POFFIN,
    BUDEW,
    CRISPIN,
    CRUSHING_HAMMER,
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
    attach_energy,
    attack_choice,
    bench_spread_target,
    boss_orders_target,
    crispin_energy_routing,
    discard_energy_target,
    discard_sequencing,
    evolve_choice,
    mulligan,
    munkidori_defensive_heal,
    play_crushing_hammer,
    play_search_for_dreepy,
    print_prize_check,
    prize_check,
    search_for_dreepy,
    supporter_tiebreak,
    track_prize_takes,
    watchtower_meowth_sequencing,
)
from pokemon.heuristics.dragapult_matchups import _matchup_bucket, archetype_latch
from pokemon.heuristics.dragapult_state import DragapultState


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
    prize: list | None = None,
    opp_prize: list | None = None,
):
    # Default to a full, untaken 6-prize pile for both sides. Real obs data
    # has every prize entry ``None`` (contents hidden even from the owner);
    # the array shrinks as prizes are taken (PKM-021) -- tests that care
    # about `prizes_remaining` pass an explicit shorter list.
    return {
        "select": select,
        "current": {
            "yourIndex": 0,
            "turn": turn,
            "stadium": stadium or [],
            "players": [
                {
                    "hand": hand or [],
                    "active": active or [],
                    "bench": bench or [],
                    "discard": discard or [],
                    "prize": prize if prize is not None else [None] * 6,
                },
                {
                    "hand": None,
                    "active": opp_active or [],
                    "bench": opp_bench or [],
                    "discard": opp_discard or [],
                    "prize": opp_prize if opp_prize is not None else [None] * 6,
                },
            ],
        },
    }


def _ctx(*args, state=None, **kwargs):
    return _build_ctx(_obs(*args, **kwargs), state if state is not None else DragapultState())


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
    state = DragapultState()
    ctx = _ctx(select, opp_bench=opp_bench, state=state)
    archetype_latch(ctx)
    assert state.archetype == "arboliva"
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
    state = DragapultState()
    ctx = _ctx(select, opp_bench=opp_bench, state=state)
    archetype_latch(ctx)
    assert state.archetype == "arboliva"
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


def test_supporter_tiebreak_prefers_crispin_when_boss_would_break_chain():
    """P1.1: a non-game-ending Boss's Orders must not consume this turn's
    Supporter play when Crispin is in hand and the chain is energy-short."""
    active = {"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": [{"id": FIRE_ENERGY}]}  # only 1 energy
    hand = [{"id": BOSS_ORDERS}, {"id": CRISPIN}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [{"type": 7, "index": 0}, {"type": 7, "index": 1}],
    }
    # Boss has a payoff (70 dmg Jet Headbutt KOs the 60 HP bench target) but
    # doesn't end the game (6 prizes still to go, target is worth only 1).
    ctx = _ctx(
        select,
        hand=hand,
        active=[active],
        opp_bench=[{"id": 1, "name": "Staryu", "hp": 60, "maxHp": 60}],
    )
    assert supporter_tiebreak(ctx) == [1]  # Crispin, not Boss's Orders


def test_supporter_tiebreak_still_plays_boss_when_it_wins_the_game():
    """P1.4: a game-ending Boss's Orders overrides the chain-preservation gate."""
    active = {"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": [{"id": FIRE_ENERGY}]}
    hand = [{"id": BOSS_ORDERS}, {"id": CRISPIN}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [{"type": 7, "index": 0}, {"type": 7, "index": 1}],
    }
    ctx = _ctx(
        select,
        hand=hand,
        active=[active],
        opp_bench=[{"id": 1, "name": "Staryu", "hp": 60, "maxHp": 60}],
        prize=[None],  # my last prize -- this KO wins the game
    )
    assert supporter_tiebreak(ctx) == [0]  # Boss's Orders


def test_boss_orders_target_prefers_ex_over_low_value_priority_target_when_chain_at_risk():
    """P1.1: once Boss's Orders is already being played on a chain-critical
    turn, an ex (2-prize) target outranks a matchup-priority one-prizer."""
    active = {"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": [{"id": FIRE_ENERGY}]}  # chain-critical
    opp_bench = [
        # id is a real catalog "ex" card (is_ex must resolve True); name is what
        # latches the "arboliva" archetype signature (`TIER5_SIGNATURES`).
        {"id": MEOWTH_EX, "name": "Arboliva ex", "hp": 300, "maxHp": 310},
        {"id": 710, "name": "Meganium", "hp": 160, "maxHp": 160},  # non-ex, IS the matchup priority target
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
    state = DragapultState()
    ctx = _ctx(select, active=[active], hand=[{"id": CRISPIN}], opp_bench=opp_bench, state=state)
    archetype_latch(ctx)
    assert state.archetype == "arboliva"
    assert boss_orders_target(ctx) == [0]  # Arboliva ex, not the (non-ex) matchup priority target


def test_boss_orders_target_uses_matchup_priority_when_chain_not_at_risk():
    """Same board, but the chain isn't at risk (already fully energized) --
    falls back to ordinary matchup-priority targeting."""
    active = {
        "id": DRAGAPULT_EX,
        "hp": 320,
        "maxHp": 320,
        "energyCards": [{"id": FIRE_ENERGY}, {"id": PSYCHIC_ENERGY}],
    }
    opp_bench = [
        {"id": 404, "name": "Arboliva ex", "hp": 300, "maxHp": 310},
        {"id": 710, "name": "Meganium", "hp": 160, "maxHp": 160},
    ]
    select = {
        "type": 1,
        "context": 3,
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0},
            {"type": 3, "area": 5, "index": 1},
        ],
    }
    state = DragapultState()
    ctx = _ctx(select, active=[active], opp_bench=opp_bench, state=state)
    archetype_latch(ctx)
    assert boss_orders_target(ctx) == [1]  # Meganium, per Section 8's priority-target note


def test_bench_spread_target_prefers_30hp_over_60hp_tier():
    """P1.3: a <=30 HP target (one Adrena-Brain shift finishes it) outranks
    a merely <=60 HP target, even with no matchup-priority archetype latched."""
    opp_bench = [
        {"id": 1, "name": "Something", "hp": 55, "maxHp": 100},
        {"id": 2, "name": "Something Else", "hp": 25, "maxHp": 100},
    ]
    select = {
        "type": 1,
        "context": 14,  # DAMAGE_COUNTER_ANY
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0, "playerIndex": 1},
            {"type": 3, "area": 5, "index": 1, "playerIndex": 1},
        ],
    }
    ctx = _ctx(select, opp_bench=opp_bench)
    assert bench_spread_target(ctx) == [1]  # the 25 HP target, not merely the 55 HP one


# --- plan 011 Phase 2: deck-id belief feeding Tier 5 targeting ---------------
#
# Synthetic two-archetype library over real catalog ids (742 Kadabra /
# 66 Dudunsparce carry the "alakazam" TIER5 signature names; 119 Dreepy
# carries none; 9 Boomerang Energy is inert filler), mirroring the fixture
# style in test_deck_id.py. Two lists in "Bot Alakazam" keep a single Kadabra
# reveal at level 2 (no unique exact list) so the core+flex classification
# path is what's exercised.

_BUCKET_LIBRARY = {
    "total_lists": 3,
    "archetypes": {
        "Bot Alakazam": {
            "meta_share": 2 / 3,
            "core": {"742": 2, "66": 3},
            "flex": {"1182": {"count_range": [0, 2], "lists_with": 1}},
            "lists": [
                {"player": "a1", "title": "Bot Alakazam", "cards": {"742": 2, "66": 3, "1182": 2, "9": 53}},
                {"player": "a2", "title": "Bot Alakazam", "cards": {"742": 2, "66": 3, "9": 55}},
            ],
        },
        "Bot Dreepy": {
            "meta_share": 1 / 3,
            "core": {"119": 4},
            "flex": {},
            "lists": [
                {"player": "b1", "title": "Bot Dreepy", "cards": {"119": 4, "9": 56}},
            ],
        },
    },
}

_NOOP_SELECT = {"type": 0, "context": 0, "maxCount": 1, "option": []}


def _bucket_identifier(*reveal_ids: int) -> DeckIdentifier:
    ident = DeckIdentifier(library=_BUCKET_LIBRARY)
    if reveal_ids:
        ident.update(
            {
                "active": [],
                "bench": [{"id": cid} for cid in reveal_ids],
                "discard": [],
                "hand": None,
                "handCount": 5,
                "deckCount": 40,
            }
        )
    return ident


def test_matchup_bucket_prefers_deck_belief_over_latch():
    """A concentrated belief (Kadabra reveal eliminates "Bot Dreepy") is
    classified through TIER5_SIGNATURES and outranks a contradicting latch."""
    ident = _bucket_identifier(742)  # Kadabra
    ctx = _ctx(_NOOP_SELECT, state=DragapultState(deck_id=ident, archetype="mega_lucario"))
    assert _matchup_bucket(ctx) == "alakazam"


def test_matchup_bucket_falls_back_to_latch_when_belief_unresolved():
    """No reveals -> level 3 -> the board-observation latch still decides."""
    ident = _bucket_identifier()
    ctx = _ctx(_NOOP_SELECT, state=DragapultState(deck_id=ident, archetype="raging_bolt"))
    assert _matchup_bucket(ctx) == "raging_bolt"


def test_matchup_bucket_falls_back_when_believed_archetype_has_no_signature():
    """"Bot Dreepy" (identified exactly after a 4-Dreepy reveal) carries no
    TIER5 signature name -- the belief abstains and the latch decides."""
    ident = _bucket_identifier(119, 119, 119, 119)
    assert ident.identified_list() is not None
    ctx = _ctx(_NOOP_SELECT, state=DragapultState(deck_id=ident, archetype="grimmsnarl"))
    assert _matchup_bucket(ctx) == "grimmsnarl"


def test_matchup_bucket_none_without_belief_or_latch():
    ctx = _ctx(_NOOP_SELECT, state=DragapultState())
    assert _matchup_bucket(ctx) is None


def test_bench_spread_target_uses_belief_priority_before_any_signature_seen():
    """Integration: with the belief concentrated on the alakazam bucket and
    NO latch (no signature Pokemon on the board yet), bench_spread_target
    pulls the bucket's priority target (Dudunsparce) over a lower-HP one."""
    opp_bench = [
        {"id": 1, "name": "Something", "hp": 25, "maxHp": 100},
        {"id": 66, "name": "Dudunsparce", "hp": 90, "maxHp": 90},
    ]
    select = {
        "type": 1,
        "context": 14,  # DAMAGE_COUNTER_ANY
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0, "playerIndex": 1},
            {"type": 3, "area": 5, "index": 1, "playerIndex": 1},
        ],
    }
    ctx = _ctx(select, opp_bench=opp_bench, state=DragapultState(deck_id=_bucket_identifier(742)))
    assert bench_spread_target(ctx) == [1]  # priority target, not the 25 HP one


def test_munkidori_defensive_heal_saves_endangered_attacker():
    """P1.2: my Dragapult ex at 50 HP is one Adrena-Brain shift (<=30) away
    from surviving the opponent's 70-damage attack next turn -- heal it
    rather than defaulting to whatever offense-only rule would otherwise win."""
    my_dragapult = {"id": DRAGAPULT_EX, "hp": 50, "maxHp": 320, "energyCards": [], "serial": 1}
    opp_active = {"id": DRAGAPULT_EX, "name": "Attacker", "hp": 200, "maxHp": 200, "energyCards": [{"id": FIRE_ENERGY}]}
    select = {
        "type": 1,
        "context": 14,  # DAMAGE_COUNTER_ANY ("move damage FROM 1 of your Pokemon")
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 4, "index": 0, "playerIndex": 0},
        ],
    }
    ctx = _ctx(select, active=[my_dragapult], opp_active=[opp_active])
    assert munkidori_defensive_heal(ctx) == [0]


def test_munkidori_defensive_heal_defers_when_no_shift_would_help():
    """Healing 30 HP wouldn't save a Pokemon facing lethal damage well beyond
    that margin -- defer rather than waste Adrena-Brain on a lost cause."""
    my_dragapult = {"id": DRAGAPULT_EX, "hp": 10, "maxHp": 320, "energyCards": [], "serial": 1}
    opp_active = {"id": DRAGAPULT_EX, "name": "Attacker", "hp": 200, "maxHp": 200, "energyCards": [{"id": FIRE_ENERGY}]}
    select = {
        "type": 1,
        "context": 14,
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 4, "index": 0, "playerIndex": 0},
        ],
    }
    ctx = _ctx(select, active=[my_dragapult], opp_active=[opp_active])
    assert munkidori_defensive_heal(ctx) is None


def test_boss_orders_target_prefers_damaged_ex_over_lower_hp_one_prizer():
    """P2.5: a damaged ex (2-prize) target outranks an even lower-HP
    one-prizer -- the two-prize value is worth more than a small HP edge."""
    opp_bench = [
        {"id": MEOWTH_EX, "name": "Some Ex", "hp": 150, "maxHp": 170},
        {"id": 999, "name": "Some Basic", "hp": 140, "maxHp": 140},
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
    ctx = _ctx(select, opp_bench=opp_bench)
    assert boss_orders_target(ctx) == [0]  # the damaged ex, despite its higher HP


def test_boss_orders_target_undamaged_ex_does_not_beat_damaged_one_prizer():
    """P2.5: an untouched, full-HP ex is not automatically worth more than an
    already-damaged one-prizer -- the two-prize preference only kicks in once
    the ex is actually damaged (a real follow-up KO is plausible)."""
    opp_bench = [
        {"id": MEOWTH_EX, "name": "Some Ex", "hp": 170, "maxHp": 170},  # untouched
        {"id": 999, "name": "Some Basic", "hp": 50, "maxHp": 140},  # already damaged
    ]
    select = {
        "type": 1,
        "context": 3,
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 5, "index": 0},
            {"type": 3, "area": 5, "index": 1},
        ],
    }
    ctx = _ctx(select, opp_bench=opp_bench)
    assert boss_orders_target(ctx) == [1]  # the damaged one-prizer, not the untouched ex


def test_attach_energy_prefers_backup_dreepy_when_active_dragapult_fully_fueled():
    """P2.7: once the active Dragapult ex can already pay Phantom Dive's
    Fire+Psychic cost, further Fire/Psychic routes to a backup Dreepy/Drakloak
    instead of topping up redundant energy on the active one."""
    active = {
        "id": DRAGAPULT_EX,
        "hp": 320,
        "maxHp": 320,
        "energyCards": [{"id": FIRE_ENERGY}, {"id": PSYCHIC_ENERGY}],
    }
    dreepy = {"id": DREEPY, "hp": 70, "maxHp": 70, "energyCards": [], "serial": 1}
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 4, "inPlayIndex": 0, "type": 8},  # ATTACH -> active
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 0, "type": 8},  # ATTACH -> bench Dreepy
        ],
    }
    ctx = _ctx(select, hand=[{"id": FIRE_ENERGY}], active=[active], bench=[dreepy])
    assert attach_energy(ctx) == [1]


def test_attach_energy_recognizes_mixed_energy_as_not_fully_fueled():
    """Regression: a prior version's ``energy_count(c) >= 2`` readiness check
    treated 2 Fire energies (no Psychic) as "fully fueled," wrongly routing
    further fuel to a backup Dreepy instead of completing the active
    Dragapult ex's actual Phantom Dive cost."""
    active = {
        "id": DRAGAPULT_EX,
        "hp": 320,
        "maxHp": 320,
        "energyCards": [{"id": FIRE_ENERGY}, {"id": FIRE_ENERGY}],  # count=2, but no Psychic
    }
    dreepy = {"id": DREEPY, "hp": 70, "maxHp": 70, "energyCards": [], "serial": 1}
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 4, "inPlayIndex": 0, "type": 8},  # ATTACH Psychic -> active
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 0, "type": 8},  # ATTACH Psychic -> bench Dreepy
        ],
    }
    ctx = _ctx(select, hand=[{"id": PSYCHIC_ENERGY}], active=[active], bench=[dreepy])
    assert attach_energy(ctx) == [0]  # completes the active attacker's real cost


def test_attach_energy_avoids_stranding_on_critically_damaged_target():
    """P2.6: a critically-damaged Dreepy is deprioritized ahead of even the
    attacker-line ordering -- fueling it strands the energy if it's lost
    before it ever attacks."""
    dreepy = {"id": DREEPY, "hp": 20, "maxHp": 70, "energyCards": [], "serial": 1}  # near death
    drakloak = {"id": DRAKLOAK, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 2}  # healthy
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 0, "type": 8},  # ATTACH Fire -> Dreepy
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 1, "type": 8},  # ATTACH Fire -> Drakloak
        ],
    }
    ctx = _ctx(select, hand=[{"id": FIRE_ENERGY}], bench=[dreepy, drakloak])
    assert attach_energy(ctx) == [1]  # Drakloak, not the near-death Dreepy


def test_attach_energy_prefers_bench_drakloak_over_active_munkidori():
    """PKM-019 batch 20260710, finding B: the old unconditional "prefer
    active" short-circuit let a non-attacker-line active (Munkidori)
    out-prioritize a bench Drakloak building toward the next Dragapult ex.
    Confirmed recurring in games 010, 014, 026."""
    munkidori = {"id": MUNKIDORI, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 1}
    drakloak = {"id": DRAKLOAK, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 2}
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"index": 0, "area": 2, "inPlayArea": 4, "inPlayIndex": 0, "type": 8},  # ATTACH Psychic -> active Munkidori
            {"index": 0, "area": 2, "inPlayArea": 5, "inPlayIndex": 0, "type": 8},  # ATTACH Psychic -> bench Drakloak
        ],
    }
    ctx = _ctx(select, hand=[{"id": PSYCHIC_ENERGY}], active=[munkidori], bench=[drakloak])
    assert attach_energy(ctx) == [1]  # Drakloak, not the active Munkidori


def test_supporter_tiebreak_plays_single_lillie_alongside_attack():
    """PKM-019 batch 20260710, finding A (Supporter half): a single legal
    Supporter next to a legal Attack used to be left for ``attack_choice``
    to win by default (the old ``len(ids) < 2`` gate). Confirmed recurring
    in games 017/020/021."""
    hand = [{"id": LILLIES_DETERMINATION}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 7, "index": 0},  # PLAY Lillie's Determination
            {"attackId": 151, "type": 13},  # Attack
        ],
    }
    ctx = _ctx(select, hand=hand, active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}])
    assert supporter_tiebreak(ctx) == [0]


def test_play_crushing_hammer_before_attack_when_opponent_has_energy():
    """PKM-019 batch 20260710, finding A (Item half): Crushing Hammer sat
    legal and unplayed for many turns in games 017/020/021 because nothing
    ever chose a standalone Item Play over ``attack_choice``."""
    hand = [{"id": CRUSHING_HAMMER}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [
            {"type": 7, "index": 0},  # PLAY Crushing Hammer
            {"attackId": 151, "type": 13},  # Attack
        ],
    }
    ctx = _ctx(
        select,
        hand=hand,
        active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}],
        opp_active=[{"id": 1, "hp": 100, "maxHp": 100, "energyCards": [{"id": FIRE_ENERGY}]}],
    )
    assert play_crushing_hammer(ctx) == [0]


def test_play_crushing_hammer_defers_when_opponent_has_no_energy():
    hand = [{"id": CRUSHING_HAMMER}]
    select = {
        "type": 0,
        "context": 0,
        "maxCount": 1,
        "option": [{"type": 7, "index": 0}, {"attackId": 151, "type": 13}],
    }
    ctx = _ctx(
        select,
        hand=hand,
        active=[{"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": []}],
        opp_active=[{"id": 1, "hp": 100, "maxHp": 100, "energyCards": []}],
    )
    assert play_crushing_hammer(ctx) is None


def test_discard_energy_target_prefers_fully_stripping_opponent_target():
    """PKM-019 batch 20260710, finding D: Crushing Hammer's own discard-target
    step had no heuristic, falling to random (confirmed recurring in games
    008, 009) -- e.g. hitting a 3-energy active for no readiness change
    instead of fully denying a 1-energy bench Pokemon's only attachment."""
    opp_active = {"id": 1, "hp": 340, "maxHp": 350, "energyCards": [{"id": FIRE_ENERGY}] * 3}
    opp_bench_target = {"id": 2, "hp": 90, "maxHp": 90, "energyCards": [{"id": FIRE_ENERGY}]}
    select = {
        "type": 1,
        "context": 30,  # DISCARD_ENERGY
        "maxCount": 1,
        "option": [
            {"type": 6, "area": 4, "index": 0, "playerIndex": 1, "energyIndex": 0},
            {"type": 6, "area": 4, "index": 0, "playerIndex": 1, "energyIndex": 1},
            {"type": 6, "area": 5, "index": 0, "playerIndex": 1, "energyIndex": 0},
        ],
    }
    ctx = _ctx(select, opp_active=[opp_active], opp_bench=[opp_bench_target])
    assert discard_energy_target(ctx) == [2]  # the bench target's only energy -- a full strip


def test_discard_energy_target_uses_own_discard_priority_for_retreat_cost():
    """The same select context, when it resolves to our own board (retreat
    cost), should use ``_discard_priority``'s ordering instead."""
    active = {
        "id": DRAGAPULT_EX,
        "hp": 320,
        "maxHp": 320,
        "energyCards": [{"id": FIRE_ENERGY}, {"id": 7}],  # Fire (low priority), Darkness (id=7, keep)
    }
    select = {
        "type": 1,
        "context": 30,  # DISCARD_ENERGY
        "maxCount": 1,
        "option": [
            {"type": 6, "area": 4, "index": 0, "playerIndex": 0, "energyIndex": 0},
            {"type": 6, "area": 4, "index": 0, "playerIndex": 0, "energyIndex": 1},
        ],
    }
    ctx = _ctx(select, active=[active])
    assert discard_energy_target(ctx) == [0]  # discard the Fire, keep the Darkness


def test_crispin_attach_to_prefers_scarcer_energy_type():
    """PKM-019 batch 20260710, finding C: Crispin's own energy-shuffle steps
    had no heuristic coverage (confirmed recurring, multi-option, in games
    010, 014, 015). We already have Fire attached somewhere -- Psychic is
    the scarcer type, so it's the better direct-attach pick."""
    dragapult = {"id": DRAGAPULT_EX, "hp": 320, "maxHp": 320, "energyCards": [{"id": FIRE_ENERGY}]}
    select = {
        "type": 1,
        "context": 22,  # ATTACH_TO
        "maxCount": 1,
        "deck": [{"id": FIRE_ENERGY}, {"id": PSYCHIC_ENERGY}],
        "option": [
            {"type": 3, "area": 1, "index": 0},
            {"type": 3, "area": 1, "index": 1},
        ],
    }
    ctx = _ctx(select, active=[dragapult])
    assert crispin_energy_routing(ctx) == [1]  # Psychic, the scarcer type


def test_crispin_attach_from_reuses_fuel_priority():
    """The ATTACH_FROM destination step reuses ``attach_energy``'s own fuel
    routing (attacker line before Munkidori)."""
    munkidori = {"id": MUNKIDORI, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 1}
    drakloak = {"id": DRAKLOAK, "hp": 90, "maxHp": 90, "energyCards": [], "serial": 2}
    select = {
        "type": 1,
        "context": 21,  # ATTACH_FROM
        "maxCount": 1,
        "option": [
            {"type": 3, "area": 4, "index": 0, "playerIndex": 0},
            {"type": 3, "area": 5, "index": 0, "playerIndex": 0},
        ],
    }
    ctx = _ctx(select, active=[munkidori], bench=[drakloak])
    assert crispin_energy_routing(ctx) == [1]  # bench Drakloak, not the active Munkidori


def test_prize_check_defers_without_a_deck_search():
    """No ``select.deck`` on this decision -- not a deck-search reveal --
    so the deduction doesn't run at all."""
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}]}
    ctx = _ctx(select)
    assert prize_check(ctx) is None
    assert ctx.state.prize_check_done is False
    assert all(not e.prized for e in ctx.state.deck_memory)


def test_prize_check_marks_exactly_the_missing_copies_as_prized():
    """DRAGAPULT_DECK has 4 Dreepy. 2 are in hand, 1 in the discard pile --
    the 4th is nowhere visible (hand/board/discard/revealed deck), so
    exactly 1 of its 4 deck_memory entries should end up marked prized."""
    hand = [{"id": DREEPY}, {"id": DREEPY}]
    discard = [{"id": DREEPY}]
    select = {
        "type": 1,
        "context": 7,  # TO_HAND (a deck-search reveal)
        "maxCount": 1,
        "deck": [],  # nothing further of Dreepy left in the deck
        "option": [{"type": 3, "area": 1, "index": 0}],
    }
    ctx = _ctx(select, hand=hand, discard=discard)
    assert prize_check(ctx) is None
    assert ctx.state.prize_check_done is True
    dreepy_entries = [e for e in ctx.state.deck_memory if e.id == DREEPY]
    assert len(dreepy_entries) == 4
    assert sum(1 for e in dreepy_entries if e.prized) == 1


def test_prize_check_accounts_for_evolved_and_attached_cards():
    """A bench Drakloak with a preEvolution-nested Dreepy, plus an active
    Dragapult ex carrying a Fire Energy attachment, must not make the
    evolved-from Dreepy or the attached Fire Energy look "missing" --
    both are still real, in-play copies, not prized ones."""
    drakloak = {
        "id": DRAKLOAK,
        "hp": 90,
        "maxHp": 90,
        "energyCards": [],
        "preEvolution": [{"id": DREEPY}],
    }
    dragapult = {
        "id": DRAGAPULT_EX,
        "hp": 320,
        "maxHp": 320,
        "energyCards": [{"id": FIRE_ENERGY}],
        "preEvolution": [{"id": DRAKLOAK}, {"id": DREEPY}],
    }
    select = {
        "type": 1,
        "context": 7,
        "maxCount": 1,
        "deck": [],
        "option": [{"type": 3, "area": 1, "index": 0}],
    }
    ctx = _ctx(select, active=[dragapult], bench=[drakloak])
    assert prize_check(ctx) is None
    dreepy_entries = [e for e in ctx.state.deck_memory if e.id == DREEPY]
    drakloak_entries = [e for e in ctx.state.deck_memory if e.id == DRAKLOAK]
    fire_entries = [e for e in ctx.state.deck_memory if e.id == FIRE_ENERGY]
    # 2 Dreepy accounted for (one per preEvolution chain) out of 4 -> 2 prized
    assert sum(1 for e in dreepy_entries if e.prized) == 2
    # 1 Drakloak accounted for (in play) + 1 (nested under the Dragapult ex) out of 4 -> 2 prized
    assert sum(1 for e in drakloak_entries if e.prized) == 2
    # the attached Fire Energy is accounted for, not prized
    assert sum(1 for e in fire_entries if e.prized) == 3  # 4 total, 1 attached


def test_prize_check_runs_only_once_per_game():
    """A second deck-search reveal later in the game must not re-run the
    deduction -- ``deck_memory`` from the first pass is left alone."""
    hand = [{"id": DREEPY}, {"id": DREEPY}]
    discard = [{"id": DREEPY}]
    select = {
        "type": 1,
        "context": 7,
        "maxCount": 1,
        "deck": [],
        "option": [{"type": 3, "area": 1, "index": 0}],
    }
    state = DragapultState()
    ctx = _ctx(select, hand=hand, discard=discard, state=state)
    prize_check(ctx)
    first_pass = [(e.id, e.prized) for e in state.deck_memory]

    # A wildly different board on the "second" call -- if this re-ran, the
    # Dreepy math above would change.
    ctx2 = _ctx(select, hand=[], discard=[], state=state)
    assert prize_check(ctx2) is None
    assert [(e.id, e.prized) for e in state.deck_memory] == first_pass


def test_print_prize_check_advances_only_on_a_new_turn():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}]}
    state = DragapultState()
    state.prize_check_done = True

    assert print_prize_check(_ctx(select, turn=5, state=state)) is None
    assert state.prize_check_printed_turn == 5

    # Same turn again -- a second decision within the same turn -- no change.
    assert print_prize_check(_ctx(select, turn=5, state=state)) is None
    assert state.prize_check_printed_turn == 5

    # New turn -- the guard advances.
    assert print_prize_check(_ctx(select, turn=6, state=state)) is None
    assert state.prize_check_printed_turn == 6


def test_print_prize_check_prints_a_placeholder_before_prize_check_has_run():
    """Prints every turn even before ``prize_check`` has completed --
    deliberately, so a real game's log shows this hook is firing every turn
    regardless of whether the deduction itself has triggered yet."""
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}]}
    ctx = _ctx(select, turn=1)
    assert print_prize_check(ctx) is None
    assert ctx.state.prize_check_printed_turn == 1


def test_print_prize_check_increments_decision_count_every_call():
    """``decision_count`` tracks every call (every action submitted to
    Kaggle), not just the once-per-turn prints."""
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}]}
    state = DragapultState()
    print_prize_check(_ctx(select, turn=1, state=state))
    print_prize_check(_ctx(select, turn=1, state=state))  # same turn, still counts as a decision
    print_prize_check(_ctx(select, turn=2, state=state))
    assert state.decision_count == 3


def test_track_prize_takes_first_call_only_snapshots():
    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}]}
    ctx = _ctx(select, hand=[{"id": DREEPY}], prize=[None] * 6)
    assert track_prize_takes(ctx) is None
    assert ctx.state.last_prize_count == 6
    assert ctx.state.last_hand_counts == {DREEPY: 1}


def test_track_prize_takes_unprizes_the_newly_revealed_card():
    """Prize count drops 6 -> 5 and Boss's Orders newly appears in hand --
    that must be the taken prize, so its deck_memory entry un-prizes."""
    state = DragapultState()
    next(e for e in state.deck_memory if e.id == BOSS_ORDERS).prized = True
    state.last_prize_count = 6
    state.last_hand_counts = {}

    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}]}
    ctx = _ctx(select, hand=[{"id": BOSS_ORDERS}], prize=[None] * 5, state=state)
    assert track_prize_takes(ctx) is None
    boss_entries = [e for e in state.deck_memory if e.id == BOSS_ORDERS]
    assert sum(1 for e in boss_entries if e.prized) == 0
    assert state.last_prize_count == 5


def test_track_prize_takes_ignores_hand_growth_without_a_prize_taken():
    """Hand grows (a normal draw) but the prize count is unchanged -- no
    prize was taken, so deck_memory must be left alone."""
    state = DragapultState()
    next(e for e in state.deck_memory if e.id == BOSS_ORDERS).prized = True
    state.last_prize_count = 6
    state.last_hand_counts = {}

    select = {"type": 0, "context": 0, "maxCount": 1, "option": [{"type": 14}]}
    ctx = _ctx(select, hand=[{"id": BOSS_ORDERS}], prize=[None] * 6, state=state)
    assert track_prize_takes(ctx) is None
    boss_entries = [e for e in state.deck_memory if e.id == BOSS_ORDERS]
    assert sum(1 for e in boss_entries if e.prized) == 1

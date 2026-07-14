"""Unit tests for `pokemon.deck_id` (PKM-023, plan 010 Phase 2).

Uses a small synthetic library (not the real `data/meta_decks/library.json`)
so the elimination logic is tested against known-exact expectations, plus a
light smoke test against the real library. Identity-bearing card ids are
real catalog ids (119 Dreepy, 120 Drakloak, 140 Fezandipiti ex -- Pokemon;
1182 Boss's Orders, 1080 Unfair Stamp -- Trainer) so `_card_weight`'s
cardType lookup resolves them as intended by the module under test; "9"
(Boomerang Energy) is used as inert filler to pad lists to 60.
"""

import pytest

from pokemon.deck_id import DeckIdentifier, load_library

SYNTH_LIBRARY = {
    "total_lists": 4,
    "archetypes": {
        "Alpha": {
            "meta_share": 0.6,
            "core": {"119": 4, "120": 2},
            "flex": {"1182": {"count_range": [0, 2], "lists_with": 1}},
            "lists": [
                {"player": "a1", "placing": "1st", "title": "Alpha", "cards": {"119": 4, "120": 2, "1182": 2, "9": 52}},
                {"player": "a2", "placing": "2nd", "title": "Alpha", "cards": {"119": 4, "120": 2, "9": 54}},
            ],
        },
        "Beta": {
            "meta_share": 0.4,
            "core": {"140": 3},
            "flex": {},
            "lists": [
                {"player": "b1", "placing": "1st", "title": "Beta", "cards": {"140": 3, "9": 57}},
                {"player": "b2", "placing": "2nd", "title": "Beta", "cards": {"140": 3, "1080": 1, "9": 56}},
            ],
        },
    },
}


def _opp(active=None, bench=None, discard=None, hand_count=6, deck_count=54):
    return {
        "active": active or [],
        "bench": bench or [],
        "discard": discard or [],
        "hand": None,
        "handCount": hand_count,
        "deckCount": deck_count,
    }


def _card(cid, energy=(), tools=(), pre_evo=()):
    return {"id": cid, "energyCards": [{"id": e} for e in energy], "tools": [{"id": t} for t in tools], "preEvolution": [{"id": p} for p in pre_evo]}


def _identifier():
    return DeckIdentifier(library=SYNTH_LIBRARY)


def test_no_reveals_is_level_3_flat_meta_prior():
    ident = _identifier()
    belief = ident.archetype_belief()
    assert belief == pytest.approx({"Alpha": 0.6, "Beta": 0.4})
    assert ident.level() == 3
    assert ident.identified_list() is None
    assert ident.opp_remaining(119) is None
    assert ident.p_in_hand(119) is None


def test_reveal_narrows_to_single_archetype_level_2():
    ident = _identifier()
    # Fezandipiti ex (Pokemon) only appears in Beta's core -- one sighting is
    # enough to blow Alpha's penalty budget and eliminate it outright.
    ident.update(_opp(active=[_card(140)]))
    belief = ident.archetype_belief()
    assert belief == pytest.approx({"Beta": 1.0})
    assert ident.level() == 2
    assert ident.identified_list() is None  # two Beta lists still both consistent


def test_full_core_plus_flex_narrows_to_exact_list_level_1():
    ident = _identifier()
    ident.update(
        _opp(
            active=[_card(119)],
            bench=[_card(119), _card(119), _card(119), _card(120), _card(120), _card(1182), _card(1182)],
        )
    )
    assert ident.level() == 1
    assert ident.identified_list() == {119: 4, 120: 2, 1182: 2, 9: 52}


def test_pokemon_overage_eliminates_lists_that_cant_explain_it():
    ident = _identifier()
    # 5 copies of Dreepy seen -- no list/core in the synthetic library allows
    # that many, and it's a Pokemon overage (weight 3) so it eliminates
    # outright regardless of budget: every list is eliminated (fringe).
    ident.update(_opp(bench=[_card(119)] * 5))
    assert ident.identified_list() is None
    assert ident.level() == 3
    # flat fallback prior, unaffected by the contradiction
    assert ident.archetype_belief() == pytest.approx({"Alpha": 0.6, "Beta": 0.4})


def test_reveal_tracking_is_cumulative_max_across_zone_moves():
    ident = _identifier()
    ident.update(_opp(discard=[_card(119), _card(119), _card(119)]))
    assert ident.reveals[119] == 3
    # card moves from discard to hand (e.g. Night Stretcher) -- count seen
    # simultaneously drops, but the running max stays at 3.
    ident.update(_opp(discard=[], hand_count=6))
    assert ident.reveals[119] == 3


def test_opp_remaining_exact_at_level_1_subtracts_seen():
    ident = _identifier()
    ident.update(_opp(active=[_card(119)], bench=[_card(119), _card(120), _card(120), _card(1182), _card(1182)]))
    assert ident.level() == 1
    lo, hi, expected = ident.opp_remaining(119)
    assert (lo, hi, expected) == (2, 2, 2.0)  # 4 total in the list, 2 seen (active + bench)


def test_pokemon_overage_eliminates_archetype_but_trainer_overage_is_tolerated():
    # 119 = Dreepy (real catalog Pokemon), 1182 = Boss's Orders (real catalog
    # Trainer) -- reused here so `_card_weight` resolves them by real cardType.
    library = {
        "total_lists": 1,
        "archetypes": {
            "Gamma": {
                "meta_share": 1.0,
                "core": {"119": 2, "1182": 1},
                "flex": {},
                "lists": [{"player": "g1", "placing": "1st", "title": "Gamma", "cards": {"119": 2, "1182": 1, "9": 57}}],
            },
        },
    }
    # Trainer overage by 1 (2 seen, cap 1) stays under the penalty budget.
    ident = DeckIdentifier(library=library)
    ident.update(_opp(discard=[_card(1182), _card(1182)]))
    assert ident.archetype_belief() == pytest.approx({"Gamma": 1.0})

    # Pokemon overage by 1 (3 seen, cap 2) blows the budget outright.
    ident = DeckIdentifier(library=library)
    ident.update(_opp(bench=[_card(119), _card(119), _card(119)]))
    assert ident.level() == 3


def test_opp_remaining_range_at_level_2_from_flex():
    ident = _identifier()
    ident.update(_opp(active=[_card(119)], bench=[_card(119), _card(119), _card(120)]))  # narrows to Alpha only
    assert ident.level() == 2
    lo, hi, _ = ident.opp_remaining(1182)  # Alpha's flex range for Boss's Orders is [0, 2]
    assert (lo, hi) == (0, 2)


def test_p_in_hand_is_zero_when_no_copies_remain():
    ident = _identifier()
    ident.update(
        _opp(
            active=[_card(119)],
            bench=[_card(119), _card(119), _card(119), _card(120), _card(120), _card(1182), _card(1182)],
        )
    )
    assert ident.level() == 1
    assert ident.p_in_hand(119) == 0.0  # all 4 copies already seen


def test_p_in_hand_is_positive_when_copies_remain_in_a_nonempty_pool():
    ident = _identifier()
    ident.update(
        _opp(
            active=[_card(119)],
            bench=[_card(119), _card(120), _card(120), _card(1182), _card(1182)],
            hand_count=6,
            deck_count=54,
        )
    )
    assert ident.level() == 1
    p = ident.p_in_hand(119)
    assert p is not None
    assert 0.0 < p < 1.0


def test_deck_belief_update_hook_is_wired_into_dragapult_heuristics():
    from pokemon.heuristics.dragapult import DRAGAPULT_HEURISTICS
    from pokemon.heuristics.dragapult_matchups import deck_belief_update

    assert deck_belief_update in DRAGAPULT_HEURISTICS


REAL_LIBRARY_PATH = None
try:
    from pokemon.deck_id import LIBRARY_PATH as REAL_LIBRARY_PATH
except ImportError:
    pass


@pytest.mark.skipif(
    REAL_LIBRARY_PATH is None or not REAL_LIBRARY_PATH.exists(),
    reason="library.json not generated — run scripts/fetch_limitless_decks.py",
)
def test_real_library_loads_and_belief_sums_to_one():
    library = load_library()
    ident = DeckIdentifier(library=library)
    belief = ident.archetype_belief()
    assert belief
    assert sum(belief.values()) == pytest.approx(1.0)
    assert ident.level() == 3  # no reveals yet

"""Unit tests for the turn-1 search objective
(``pokemon.heuristics.opening_score.opening_turn_score``) -- synthetic
``TurnLine``/``end_obs`` dicts, no engine/WSL required.
"""

from pokemon.heuristics.dragapult import (
    BUDDY_BUDDY_POFFIN,
    BUDEW,
    DRAKLOAK,
    DREEPY,
    FIRE_ENERGY,
    JUDGE,
    LILLIES_DETERMINATION,
    MUNKIDORI,
    POKE_PAD,
    ULTRA_BALL,
)
from pokemon.heuristics.opening_score import opening_turn_score
from pokemon.search_function import TurnLine


def _card(cid: int, energy: bool = False) -> dict:
    card = {"id": cid}
    if energy:
        card["energyCards"] = [{"id": FIRE_ENERGY}]
    return card


def _line(active=None, bench=None, hand=None, discard=None) -> TurnLine:
    end_obs = {
        "current": {
            "players": [
                {
                    "active": [active] if active else [],
                    "bench": bench or [],
                    "hand": hand or [],
                    "discard": discard or [],
                },
                {},
            ],
        }
    }
    return TurnLine(actions=[[0]], end_obs=end_obs, terminal="eot")


def test_no_end_obs_returns_the_safe_all_zero_tuple():
    line = TurnLine(actions=[[0]], end_obs=None, terminal="error")
    assert opening_turn_score(line, root_player=0) == (0, 0, 0, 0, 0, 0, 0, -1)


def test_more_dreepy_in_play_scores_higher_all_else_equal():
    two_dreepy = _line(bench=[_card(DREEPY), _card(DREEPY)])
    three_dreepy = _line(bench=[_card(DREEPY), _card(DREEPY), _card(DREEPY)])
    assert opening_turn_score(three_dreepy, 0) > opening_turn_score(two_dreepy, 0)


def test_dreepy_count_caps_at_three():
    three_dreepy = _line(bench=[_card(DREEPY)] * 3)
    four_dreepy = _line(bench=[_card(DREEPY)] * 4)
    assert opening_turn_score(three_dreepy, 0) == opening_turn_score(four_dreepy, 0)


def test_good_second_turn_outranks_raw_dreepy_count():
    """A judgment call documented on opening_turn_score itself: "make sure
    you have a good 2nd turn" is treated as the higher-priority gate, so
    fewer Dreepy with a Drakloak in hand beats more Dreepy without one."""
    many_dreepy_no_plan = _line(bench=[_card(DREEPY)] * 3, hand=[_card(1182)])  # Boss's Orders, no plan
    fewer_dreepy_with_plan = _line(bench=[_card(DREEPY)], hand=[_card(DRAKLOAK)])
    assert opening_turn_score(fewer_dreepy_with_plan, 0) > opening_turn_score(many_dreepy_no_plan, 0)


def test_lillies_or_judge_in_hand_also_counts_as_a_good_second_turn():
    with_lillies = _line(hand=[_card(LILLIES_DETERMINATION)])
    with_judge = _line(hand=[_card(JUDGE)])
    with_neither = _line(hand=[_card(1182)])  # Boss's Orders only
    assert opening_turn_score(with_lillies, 0) > opening_turn_score(with_neither, 0)
    assert opening_turn_score(with_judge, 0) > opening_turn_score(with_neither, 0)


def test_energy_attached_to_dreepy_or_munkidori_scores_higher():
    fueled = _line(bench=[_card(DREEPY, energy=True)])
    unfueled = _line(bench=[_card(DREEPY, energy=False)])
    assert opening_turn_score(fueled, 0) > opening_turn_score(unfueled, 0)

    fueled_munkidori = _line(bench=[_card(MUNKIDORI, energy=True)])
    unfueled_munkidori = _line(bench=[_card(MUNKIDORI, energy=False)])
    assert opening_turn_score(fueled_munkidori, 0) > opening_turn_score(unfueled_munkidori, 0)


def test_budew_active_scores_higher_only_when_actually_active():
    budew_active = _line(active=_card(BUDEW))
    budew_benched = _line(bench=[_card(BUDEW)])
    assert opening_turn_score(budew_active, 0) > opening_turn_score(budew_benched, 0)


def test_dead_hand_is_penalized_unless_a_good_second_turn_is_lined_up():
    empty_hand_no_plan = _line(hand=[])
    empty_hand_with_plan = _line(hand=[_card(DRAKLOAK)])
    healthy_hand_no_plan = _line(hand=[_card(1182), _card(1198)])  # Boss's Orders, Crispin
    assert opening_turn_score(empty_hand_no_plan, 0) < opening_turn_score(healthy_hand_no_plan, 0)
    assert opening_turn_score(empty_hand_no_plan, 0) < opening_turn_score(empty_hand_with_plan, 0)


def test_wasted_ultra_ball_is_penalized_when_a_higher_priority_item_was_available():
    """Item-priority proxy: Ultra Ball is lowest priority per the guideline
    (buddy-buddy poffin > poke pad > ultra ball) -- burning it while a
    higher-priority item sat unused in hand should score worse."""
    wasted = _line(hand=[_card(BUDDY_BUDDY_POFFIN)], discard=[_card(ULTRA_BALL)])
    not_wasted = _line(hand=[_card(BUDDY_BUDDY_POFFIN)], discard=[])
    assert opening_turn_score(not_wasted, 0) > opening_turn_score(wasted, 0)

    wasted_vs_poke_pad = _line(hand=[_card(POKE_PAD)], discard=[_card(ULTRA_BALL)])
    assert opening_turn_score(_line(hand=[_card(POKE_PAD)], discard=[]), 0) > opening_turn_score(
        wasted_vs_poke_pad, 0
    )


def test_ultra_ball_in_discard_is_fine_if_nothing_higher_priority_was_available():
    """No penalty if Buddy-Buddy Poffin/Poke Pad weren't even in hand --
    Ultra Ball wasn't actually jumping the priority order in that case."""
    used_ultra_ball_only = _line(hand=[], discard=[_card(ULTRA_BALL)])
    # Same as the "dead hand" case otherwise -- isolate the item-priority
    # component by comparing against an equally empty hand with no discard.
    no_items_used = _line(hand=[], discard=[])
    assert opening_turn_score(used_ultra_ball_only, 0) == opening_turn_score(no_items_used, 0)

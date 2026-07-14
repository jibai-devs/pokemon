"""Unit tests for the general-purpose search objective
(``pokemon.heuristics.smart_score.dragapult_smart_score``) -- synthetic
``TurnLine``/``end_obs`` dicts, no engine/WSL required. Uses real card ids
so ``best_attack_damage``/``can_attack_now`` resolve against the actual
catalog data (same convention as ``tests/test_heuristics_dragapult.py``).
"""

from pokemon.heuristics.dragapult import (
    BOSS_ORDERS,
    DRAGAPULT_EX,
    FEZANDIPITI_EX,
    FIRE_ENERGY,
    MEOWTH_EX,
    PSYCHIC_ENERGY,
    ULTRA_BALL,
)
from pokemon.heuristics.smart_score import dragapult_smart_score
from pokemon.search_function import TurnLine


def _card(cid: int, hp: int | None = None, max_hp: int | None = None, energy_ids=None) -> dict:
    card = {"id": cid}
    if hp is not None:
        card["hp"] = hp
    if max_hp is not None:
        card["maxHp"] = max_hp
    if energy_ids:
        card["energyCards"] = [{"id": e} for e in energy_ids]
    return card


def _line(my_active=None, my_bench=None, my_discard=None, opp_active=None) -> TurnLine:
    end_obs = {
        "current": {
            "players": [
                {
                    "active": [my_active] if my_active else [],
                    "bench": my_bench or [],
                    "discard": my_discard or [],
                    "prize": [None] * 6,
                },
                {
                    "active": [opp_active] if opp_active else [],
                    "bench": [],
                    "discard": [],
                    "prize": [None] * 6,
                },
            ],
        }
    }
    return TurnLine(actions=[[0]], end_obs=end_obs, terminal="eot")


def test_no_end_obs_returns_the_safe_all_zero_tuple():
    line = TurnLine(actions=[[0]], end_obs=None, terminal="error")
    assert dragapult_smart_score(line, root_player=0) == (0, 0, 0, 0, 0, 0, 0, -1)


def test_attacker_surviving_scores_higher_than_dying():
    healthy_active = _card(DRAGAPULT_EX, hp=320, max_hp=320)
    weak_opp = _card(DRAGAPULT_EX, hp=200, max_hp=200, energy_ids=[FIRE_ENERGY])  # can't PD, no Psychic
    dying_active = _card(DRAGAPULT_EX, hp=5, max_hp=320)
    strong_opp = _card(DRAGAPULT_EX, hp=200, max_hp=200, energy_ids=[FIRE_ENERGY, PSYCHIC_ENERGY])  # can PD

    survives = _line(my_active=healthy_active, opp_active=weak_opp)
    dies_no_backup = _line(my_active=dying_active, opp_active=strong_opp)
    assert dragapult_smart_score(survives, 0) > dragapult_smart_score(dies_no_backup, 0)


def test_backup_attacker_softens_the_penalty_when_the_attacker_would_die():
    dying_active = _card(DRAGAPULT_EX, hp=5, max_hp=320)
    strong_opp = _card(DRAGAPULT_EX, hp=200, max_hp=200, energy_ids=[FIRE_ENERGY, PSYCHIC_ENERGY])
    ready_backup = _card(DRAGAPULT_EX, hp=320, max_hp=320, energy_ids=[FIRE_ENERGY, PSYCHIC_ENERGY])

    with_backup = _line(my_active=dying_active, my_bench=[ready_backup], opp_active=strong_opp)
    without_backup = _line(my_active=dying_active, my_bench=[], opp_active=strong_opp)
    assert dragapult_smart_score(with_backup, 0) > dragapult_smart_score(without_backup, 0)
    # Still worse than not dying at all -- a backup softens, doesn't erase, the loss.
    survives = _line(my_active=_card(DRAGAPULT_EX, hp=320, max_hp=320), opp_active=strong_opp)
    assert dragapult_smart_score(survives, 0) > dragapult_smart_score(with_backup, 0)


def test_overextension_penalizes_exposed_rule_box_pokemon():
    """Fezandipiti ex / Meowth ex have no self-protection when benched
    (unlike Dragapult ex's Tera ability) -- deck/dragapult_deck_explanation.md
    Section 5's "don't hand them an easy map"."""
    exposed = _line(my_bench=[_card(FEZANDIPITI_EX), _card(MEOWTH_EX)])
    safe = _line(my_bench=[])
    assert dragapult_smart_score(safe, 0) > dragapult_smart_score(exposed, 0)


def test_discard_cost_prefers_cheaper_discards():
    """Reuses dragapult.py's own _discard_priority ranking (Section 11):
    Ultra Ball (no recursion value once spent) is cheap to lose; Boss's
    Orders is one of the most load-bearing cards in the deck."""
    cheap_discard = _line(my_discard=[_card(ULTRA_BALL)])
    expensive_discard = _line(my_discard=[_card(BOSS_ORDERS)])
    assert dragapult_smart_score(cheap_discard, 0) > dragapult_smart_score(expensive_discard, 0)

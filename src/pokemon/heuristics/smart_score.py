"""General-purpose search objective for "dragapult_smarter_search".

Combines two sources, translated into a scorable end-of-turn objective the
same way ``opening_score.py`` does for turn 1 -- not a literal port of
either's prose/flowchart shape, since the search itself explores the option
tree; this only judges which resulting board state best matches their
stated priorities:

- ``deck/guidelines_for_phantom_dive.txt`` -- the attack-or-hold-back
  decision tree (approximated as ``attacker_survival_score`` below; see its
  docstring for exactly which parts of the flowchart are and aren't
  representable within a single-turn search horizon).
- ``deck/dragapult_deck_explanation.md`` Sections 5 ("Prize-race /
  Prize-mapping concepts") and 11 ("Discard-sequencing guidance") -- the
  overextension and discard-cost components below.

Reuses existing hand-written helpers from ``pokemon.heuristics.dragapult``
(``best_attack_damage``, ``can_attack_now``, ``_discard_priority``) rather
than reimplementing them, since they already operate on plain ``CardState``
dicts (no ``Ctx`` needed) and this module's leaves (``TurnLine.end_obs``)
carry the same shape.
"""

from pokemon.heuristics.dragapult import (
    DRAGAPULT_EX,
    DRAKLOAK,
    DREEPY,
    FEZANDIPITI_EX,
    MEOWTH_EX,
    _discard_priority,
    best_attack_damage,
    can_attack_now,
)
from pokemon.search_function import TurnLine
from pokemon.types import CardState, PlayerState

_TERM_RANK = {
    "win": 5,
    "eot": 3,
    "budget": 2,
    "depth": 2,
    "draw": 1,
    "opp_choice": 1,
    "loss": 0,
    "error": -1,
}

_ATTACKER_LINE = (DREEPY, DRAKLOAK, DRAGAPULT_EX)
_EXPOSED_RULE_BOX = (FEZANDIPITI_EX, MEOWTH_EX)


def _active(player: PlayerState) -> CardState | None:
    active = player.get("active") or []
    return active[0] if active else None


def _bench(player: PlayerState) -> list[CardState]:
    return player.get("bench") or []


def _board(player: PlayerState) -> list[CardState]:
    active = _active(player)
    return ([active] if active else []) + _bench(player)


def dragapult_smart_score(line: TurnLine, root_player: int) -> tuple:
    """Higher is better. Judges the board state at the end of any turn
    (not turn-1-specific -- see ``opening_score.opening_turn_score`` for
    that) against the sources above:

    1. game result safety net -- same convention as ``score_line``
    2. own prizes remaining (fewer = better) -- same as ``score_line``
    3. opponent prizes remaining (more left = better) -- same as
       ``score_line``
    4. damage on opponent's Active (higher = better) -- same as
       ``score_line``
    5. attacker survival -- ``deck/guidelines_for_phantom_dive.txt``'s core
       criterion, approximated within a single-turn search horizon: does
       our own Active (presumably whatever just attacked) survive the
       opponent's best *currently visible* return attack, computed the same
       way ``best_attack_damage`` already does elsewhere in this codebase?
       If it wouldn't survive, is there a backup attacker (another
       attacker-line Pokemon already energy-ready via ``can_attack_now``)
       to fall back on? This only covers the flowchart's directly
       observable half -- "if I PD, will I win" is already fully covered
       by ``term_rank`` (a lethal KO shows up as ``"win"`` there), and the
       flowchart's own forward-looking half ("can I find a Drakloak/Crispin
       *next* turn") is a multi-turn lookahead this single-turn search
       can't see; ``can_attack_now`` on the *current* board is the
       nearest same-turn proxy for "do I already have a next attacker
       lined up," not a full replacement for that recursive check.
    6. overextension penalty -- ``dragapult_deck_explanation.md`` Section
       5's "don't hand them an easy map": Fezandipiti ex/Meowth ex are
       rule-box (ex) but have no self-protection when benched (unlike
       Dragapult ex's Tera ability), so each one left exposed is a free
       Boss's Orders target
    7. discard-pile cost -- reuses ``_discard_priority``'s existing "least
       costly to lose" ranking (``dragapult_deck_explanation.md`` Section
       11) summed over the whole discard pile; since every candidate line
       being compared shares the same starting discard contents, this sum
       is still a valid *relative* ranking even though it isn't a
       this-turn-only diff
    8. shorter action sequences, tie-break -- same convention as
       ``score_line``
    """
    if line.end_obs is None:
        return (0, 0, 0, 0, 0, 0, 0, -len(line.actions))

    term_rank = _TERM_RANK.get(line.terminal, 0)

    current = line.end_obs.get("current") or {}
    players = current.get("players") or []
    me = players[root_player] if len(players) > root_player else {}
    opp_idx = 1 - root_player
    opp = players[opp_idx] if len(players) > opp_idx else {}

    my_prizes = len(me.get("prize") or []) if me else 6
    opp_prizes = len(opp.get("prize") or []) if opp else 0

    opp_active = _active(opp)
    opp_damage = 0
    if opp_active is not None:
        max_hp, hp = opp_active.get("maxHp"), opp_active.get("hp")
        if max_hp is not None and hp is not None:
            opp_damage = int(max_hp) - int(hp)

    my_active = _active(me)
    my_active_hp = (my_active or {}).get("hp") or 0
    opp_best_dmg = best_attack_damage(opp_active)
    survives = my_active is None or opp_best_dmg == 0 or my_active_hp > opp_best_dmg

    if survives:
        attacker_survival_score = 1
    else:
        backup_ready = any(
            c is not None and c is not my_active and c.get("id") in _ATTACKER_LINE and can_attack_now(c)
            for c in _board(me)
        )
        attacker_survival_score = 0 if backup_ready else -1

    exposed_count = sum(
        1 for c in _board(me) if c is not None and c.get("id") in _EXPOSED_RULE_BOX
    )
    overextension_penalty = -exposed_count

    discard_ids = [c.get("id") for c in (me.get("discard") or []) if c and c.get("id") is not None]
    discard_cost = sum(_discard_priority(cid) for cid in discard_ids)

    return (
        term_rank,
        -my_prizes,
        opp_prizes,
        opp_damage,
        attacker_survival_score,
        overextension_penalty,
        -discard_cost,
        -len(line.actions),
    )
